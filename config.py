SECTIONS = {
    "model": {
        "rules": {
            "Face (5 Angles) & Body": [
                "Extract EXACT same face from the 5 provided face reference images (ATTACHED IMAGE {img_1_idx} - {img_5_idx}).",
                "Extract EXACT same body figure, proportions, and skin tone from the body reference (ATTACHED IMAGE {img_6_idx}).",
                "ATTACHED IMAGE {img_1_idx}: Front face - primary features.",
                "ATTACHED IMAGE {img_2_idx}: Left side (90 degree) face profile.",
                "ATTACHED IMAGE {img_3_idx}: Right side (90 degree) face profile.",
                "ATTACHED IMAGE {img_4_idx}: Slightly turned left (45 degree) face.",
                "ATTACHED IMAGE {img_5_idx}: Slightly turned right (45 degree) face.",
                "ATTACHED IMAGE {img_6_idx}: Body reference - extract ONLY body proportions and figure.",
                "Maintain EXACT facial structure and body proportions across all generated images.",
                "IGNORE background and clothing from all reference images."
            ],
            "Face & Body": [
                "Extract EXACT same face from model reference - eyes, nose, mouth, facial structure, skin tone, facial proportions must match exactly",
                "Extract EXACT same body figure and proportions from model reference",
                "IGNORE background, clothing, outfit, accessories, and any other elements from model reference",
            ],
            "Hair": [
                "Extract ONLY hairstyle, hair texture, and styling",
                "IGNORE face features, body, clothing, background"
            ],
            "Pose": [
                "Extract ONLY body pose, positioning, and stance",
                "IGNORE face, clothing, outfit, background, and any other elements",
                "Use ONLY the body positioning and pose with {strength}% similarity"
            ]
        }
    },
    "outfits": {
        "rules": {
            "default": [
                "Extract ONLY the {type} from outfit reference",
                "IGNORE any person, model, face, body, or background",
                "If person is wearing outfit, extract ONLY clothing items and ignore person completely",
                "Apply outfit to model maintaining design, texture, color, and details"
            ]
        }
    },
    "accessories": {
        "rules": {
            "default": [
                "Extract ONLY the {type} from reference",
                "IGNORE any person, model, face, body, or background",
                "Apply {type} to appropriate location on model"
            ]
        }
    },
    "environment": {
        "rules": {
            "Background": [
                "Extract ONLY background/environment/scene from reference",
                "IGNORE any person, model, face, body, clothing, or foreground elements"
            ],
            "Aesthetic": ["Apply {type} style: {text}"],
            "Framing": ["Apply {type} framing: {text}"],
            "Lighting": ["Apply {type} lighting: {text}"],
            "Shadows": ["Apply shadow style: {text}"]
        }
    },
    "output": {
        "quality_rules": [
            "realistic head to body ratio, ultra-detailed, highly realistic",
            "professional photography, 8k uhd, cinematic lighting, soft natural light",
            "sharp focus, perfect skin texture, lifelike eyes, accurate facial proportions",
            "volumetric depth, subtle shadows, realistic skin tones, detailed hair strands",
            "fine pores, depth of field, masterpiece, award-winning portrait style"
        ],
        "batch_consistency_rules": [
            "Model's face, body figure, outfit, clothing, jewelry, accessories must remain EXACTLY THE SAME across all images",
            "Only camera angles, poses, lighting variations, and composition can differ between images"
        ]
    }
}

BATCH_VARIATIONS = {
    "dynamic_angles": [
        "Different camera angle", "Alternative composition", "Varied perspective",
        "Different lighting angle", "Alternative framing", "Shifted viewpoint"
    ],
    "subtle_variations": [
        "Slight expression variation", "Minor pose adjustment", "Subtle lighting change"
    ]
}
