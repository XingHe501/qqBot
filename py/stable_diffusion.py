import replicate


def get_stable_diffusion_img(json,api_token):
    model = replicate.Client(api_token=api_token).models.get(
        "stability-ai/stable-diffusion")
    version = model.versions.get("db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf")
    inputs = {
        # 提示词
        'prompt': json['prompt'],
        # 分辨率
        'image_dimensions': json['image_dimensions'],
        # 反向提示词
        'negative_prompt': json['negative_prompt'],
        # 输出图片数量
        # Range: 1 to 4
        'num_outputs': 1,
        # Number of denoising steps
        # Range: 1 to 500
        'num_inference_steps': 50,

        # Scale for classifier-free guidance
        # Range: 1 to 20
        'guidance_scale': 7.5,

        # Choose a scheduler.
        'scheduler': json['scheduler'],

        # Random seed. Leave blank to randomize the seed
        # 'seed': ...,
    }
    output = version.predict(**inputs)
    return output


if __name__ == '__main__':
    print(get_stable_diffusion_img({
        "prompt": "an astronaut riding a horse on mars artstation, hd, dramatic lighting, detailed",
        "image_dimensions": "768x768",
        "negative_prompt": "",
        "scheduler": "K_EULER"
    },""))
