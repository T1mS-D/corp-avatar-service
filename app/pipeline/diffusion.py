"""GPU-пайплайн: замена фона + замена одежды (SD inpainting) + IP-Adapter FaceID + мульт-стиль.

Как сохраняется лицо (три уровня защиты):
  1. ЖЁСТКАЯ: зона головы (всё выше линии шеи) физически не входит в маску inpaint —
     в итоговом кадре эти пиксели побайтно равны оригиналу (финальный композит по маске).
  2. МЯГКАЯ: IP-Adapter FaceID подмешивает ArcFace-эмбеддинг лица в генерацию
     (критично для мульт-стиля, где лицо перерисовывается; в фото-стиле помогает согласовать шею/воротник).
  3. КОНТРОЛЬ: ArcFace-сходство «оригинал ↔ результат» ≥ порога, иначе повтор с другим seed
     (для мульта — ещё и со сниженным strength), затем статус failed.
"""
import time

import cv2
import numpy as np
from PIL import Image

from app.config import Settings
from app.pipeline import verify
from app.pipeline.background import make_background
from app.pipeline.base import AvatarPipeline, PipelineResult
from app.pipeline.faces import FaceAnalyzer, FaceInfo
from app.pipeline.preprocess import crop_head_shoulders, load_image
from app.pipeline.segmentation import composite, person_mask
from app.pipeline.styles import get_style


class DiffusionPipeline(AvatarPipeline):
    name = "diffusion"

    def __init__(self, settings: Settings):
        self.s = settings
        self._inpaint = None
        self._img2img = None

    # ------------------------------------------------------------------ загрузка моделей
    def _torch(self):
        import torch

        return torch

    def _finish_load(self, pipe):
        torch = self._torch()
        pipe.load_ip_adapter(
            self.s.ip_adapter_repo, subfolder=None,
            weight_name=self.s.ip_adapter_weight, image_encoder_folder=None,
        )
        pipe.set_ip_adapter_scale(self.s.ip_adapter_scale)
        if torch.cuda.is_available():
            if self.s.cpu_offload:
                pipe.enable_model_cpu_offload()
            else:
                pipe.to("cuda")
            pipe.enable_attention_slicing()
        return pipe

    def _dtype(self):
        torch = self._torch()
        return torch.float16 if torch.cuda.is_available() else torch.float32

    def _get_inpaint(self):
        if self._inpaint is None:
            from diffusers import AutoPipelineForInpainting

            pipe = AutoPipelineForInpainting.from_pretrained(self.s.sd_inpaint_model, torch_dtype=self._dtype())
            self._inpaint = self._finish_load(pipe)
        return self._inpaint

    def _get_img2img(self):
        if self._img2img is None:
            from diffusers import AutoPipelineForImage2Image

            pipe = AutoPipelineForImage2Image.from_pretrained(self.s.sd_img2img_model, torch_dtype=self._dtype())
            if self.s.cartoon_lora_path:
                pipe.load_lora_weights(self.s.cartoon_lora_path)
            self._img2img = self._finish_load(pipe)
        return self._img2img

    # ------------------------------------------------------------------ вспомогательное
    def _id_embeds(self, face: FaceInfo):
        """Формат из документации diffusers для IP-Adapter FaceID: [neg; pos] по оси CFG."""
        torch = self._torch()
        ref = torch.from_numpy(face.embedding).unsqueeze(0)            # (1,512)
        ref = torch.stack([ref], dim=0).unsqueeze(0)                    # (1,1,1,512)
        neg = torch.zeros_like(ref)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        return torch.cat([neg, ref]).to(dtype=self._dtype(), device=dev)

    def _repaint_mask(self, person: np.ndarray, face_c: FaceInfo, size: int) -> np.ndarray:
        """Маска одежды: тело ниже шеи (расширенное на «объём» пиджака). Голова в маску не попадает."""
        body = (person > 0.5).astype(np.uint8)
        k = max(3, int(size * 0.04))
        body = cv2.dilate(body, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        neck_y = face_c.chin_y + self.s.neck_offset_ratio * face_c.face_height
        body[: int(neck_y), :] = 0
        return body.astype(np.float32)

    def _gen(self, seed: int):
        return self._torch().Generator(device="cpu").manual_seed(int(seed))

    # ------------------------------------------------------------------ основной сценарий
    def run(self, image_path: str, style_id: str, seed: int | None = None) -> PipelineResult:
        t0 = time.time()
        style = get_style(style_id)
        size = self.s.diffusion_size
        base_seed = seed if seed is not None else int(np.random.randint(0, 2**31 - 1))

        img = load_image(image_path)
        face, m_in = verify.check_input(np.asarray(img), self.s)
        crop = crop_head_shoulders(img, face, size)

        # лицо в координатах кропа (для линии шеи)
        faces_c = FaceAnalyzer.get().analyze(np.asarray(crop))
        if not faces_c:
            raise RuntimeError("Лицо потеряно после кадрирования")
        face_c = faces_c[0]

        person = person_mask(crop)
        bg = make_background(style.background, size, self.s.brand_primary_color,
                             self.s.brand_secondary_color, style.id)
        base = composite(crop, bg, person)

        if style.kind == "cartoon":
            best = self._run_cartoon(base, face, face_c, style, base_seed)
        else:
            best = self._run_photo(base, person, face, face_c, style, base_seed)

        out, m_out, attempt = best
        out = out.resize((self.s.output_size, self.s.output_size), Image.LANCZOS)
        metrics = {**m_in, **m_out, "backend": self.name, "attempts_used": attempt,
                   "seconds": round(time.time() - t0, 2)}
        return PipelineResult(
            image=out, metrics=metrics, passed=m_out["passed"],
            message=None if m_out["passed"] else "Не пройдена проверка сохранности лица",
        )

    def _run_photo(self, base, person, face, face_c, style, base_seed):
        torch = self._torch()
        size = base.size[0]
        pipe = self._get_inpaint()
        rep = self._repaint_mask(person, face_c, size)
        mask_img = Image.fromarray((rep * 255).astype(np.uint8), "L")
        soft = cv2.GaussianBlur(rep, (0, 0), 3.0)[..., None]
        base_arr = np.asarray(base, dtype=np.float32)
        id_embeds = self._id_embeds(face)
        best = None
        for i in range(self.s.max_attempts):
            with torch.inference_mode():
                gen = pipe(
                    prompt=style.prompt, negative_prompt=style.negative_prompt,
                    image=base, mask_image=mask_img, height=size, width=size,
                    num_inference_steps=self.s.diffusion_steps, guidance_scale=7.0,
                    generator=self._gen(base_seed + i), ip_adapter_image_embeds=[id_embeds],
                ).images[0]
            # финальный композит: вне маски — байт-в-байт оригинал (жёсткое сохранение лица)
            g = np.asarray(gen.convert("RGB"), dtype=np.float32)
            final = Image.fromarray(np.clip(g * soft + base_arr * (1 - soft), 0, 255).astype(np.uint8))
            m = verify.check_output(face, np.asarray(final), self.s.face_sim_threshold)
            if best is None or m["similarity"] > best[1]["similarity"]:
                best = (final, m, i + 1)
            if m["passed"]:
                break
        return best

    def _run_cartoon(self, base, face, face_c, style, base_seed):
        torch = self._torch()
        size = base.size[0]
        pipe = self._get_img2img()
        id_embeds = self._id_embeds(face)
        best = None
        for i in range(self.s.max_attempts):
            strength = max(0.35, 0.65 - 0.08 * i)   # с каждой попыткой ближе к оригиналу
            with torch.inference_mode():
                gen = pipe(
                    prompt=style.prompt, negative_prompt=style.negative_prompt, image=base,
                    strength=strength, num_inference_steps=self.s.diffusion_steps, guidance_scale=7.0,
                    generator=self._gen(base_seed + i), ip_adapter_image_embeds=[id_embeds],
                ).images[0].convert("RGB")
            m = verify.check_output(face, np.asarray(gen), self.s.face_sim_threshold_cartoon)
            m["strength"] = round(strength, 2)
            if best is None or m["similarity"] > best[1]["similarity"]:
                best = (gen, m, i + 1)
            if m["passed"]:
                break
        return best
