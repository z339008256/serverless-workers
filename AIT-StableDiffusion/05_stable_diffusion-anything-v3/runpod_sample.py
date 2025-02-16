''' infer.py for runpod worker '''

import os
import predict

from aitemplate.testing.benchmark_pt import benchmark_torch_function
from diffusers import EulerDiscreteScheduler
from pipeline_stable_diffusion_ait import StableDiffusionAITPipeline

import runpod
from runpod.serverless.utils import upload, validator


MODEL = predict.Predictor()
MODEL.setup()


INPUT_VALIDATIONS = {
    'prompt': {
        'type': str,
        'required': True
    },
    'negative_prompt': {
        'type': str,
        'required': False
    },
    'width': {
        'type': int,
        'required': False
    },
    'height': {
        'type': int,
        'required': False
    },
    'prompt_strength': {
        'type': float,
        'required': False
    },
    'num_outputs': {
        'type': int,
        'required': False
    },
    'num_inference_steps': {
        'type': int,
        'required': False
    },
    'guidance_scale': {
        'type': float,
        'required': False
    },
    'scheduler': {
        'type': str,
        'required': False
    },
    'seed': {
        'type': int,
        'required': False
    },
    'nsfw': {
        'type': bool,
        'required': False
    }
}


def run(job):
    '''
    Run inference on the model.
    Returns output path, width the seed used to generate the image.
    '''
    model_id = "stabilityai/stable-diffusion-2"
    scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")

    pipe = StableDiffusionAITPipeline.from_pretrained(
        model_id,
        scheduler=scheduler,
        revision="fp16",
        torch_dtype=torch.float16,
        use_auth_token=token,
    ).to("cuda")

    job_input = job['input']

    input_errors = validator.validate(job_input, INPUT_VALIDATIONS)
    if input_errors:
        return {
            "error": input_errors
        }

    job_input['seed'] = job_input.get('seed', int.from_bytes(os.urandom(2), "big"))

    MODEL.NSFW = job_input.get('nsfw', True)

    img_paths = pipe(
        prompt=job_input["prompt"],
        negative_prompt=job_input.get("negative_prompt", None),
        width=job_input.get('width', 512),
        height=job_input.get('height', 512),
        num_outputs=job_input.get('num_outputs', 1),
        num_inference_steps=job_input.get('num_inference_steps', 50),
        guidance_scale=job_input.get('guidance_scale', 7.5),
        scheduler=job_input.get('scheduler', "KLMS"),
        seed=job_input.get('seed', None)
    )

    job_output = []

    for index, img_path in enumerate(img_paths):
        image_url = upload.upload_image(job['id'], img_path, index)

        job_output.append({
            "image": image_url,
            "seed": job_input['seed'] + index
        })

    return job_output


runpod.serverless.start({"handler": run})