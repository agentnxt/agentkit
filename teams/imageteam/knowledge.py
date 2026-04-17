"""
Built-in knowledge — social media image dimensions, aspect ratios, best practices.
The agent uses this to auto-set correct dimensions based on platform.
"""

SOCIAL_MEDIA_DIMENSIONS = {
    "facebook": {
        "post": {"width": 1200, "height": 630, "aspect": "1.91:1"},
        "cover": {"width": 820, "height": 312, "aspect": "2.63:1"},
        "profile": {"width": 170, "height": 170, "aspect": "1:1"},
        "story": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "event_cover": {"width": 1920, "height": 1005, "aspect": "1.91:1"},
        "ad_single": {"width": 1200, "height": 628, "aspect": "1.91:1"},
        "ad_carousel": {"width": 1080, "height": 1080, "aspect": "1:1"},
        "video_thumbnail": {"width": 1280, "height": 720, "aspect": "16:9"},
    },
    "instagram": {
        "post_square": {"width": 1080, "height": 1080, "aspect": "1:1"},
        "post_portrait": {"width": 1080, "height": 1350, "aspect": "4:5"},
        "post_landscape": {"width": 1080, "height": 566, "aspect": "1.91:1"},
        "story": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "reel": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "profile": {"width": 320, "height": 320, "aspect": "1:1"},
        "carousel": {"width": 1080, "height": 1080, "aspect": "1:1"},
        "ad": {"width": 1080, "height": 1080, "aspect": "1:1"},
    },
    "linkedin": {
        "post": {"width": 1200, "height": 627, "aspect": "1.91:1"},
        "banner": {"width": 1584, "height": 396, "aspect": "4:1"},
        "profile": {"width": 400, "height": 400, "aspect": "1:1"},
        "company_logo": {"width": 300, "height": 300, "aspect": "1:1"},
        "company_cover": {"width": 1128, "height": 191, "aspect": "5.91:1"},
        "article_cover": {"width": 1200, "height": 644, "aspect": "1.86:1"},
        "ad": {"width": 1200, "height": 627, "aspect": "1.91:1"},
        "carousel": {"width": 1080, "height": 1080, "aspect": "1:1"},
    },
    "twitter": {
        "post": {"width": 1200, "height": 675, "aspect": "16:9"},
        "header": {"width": 1500, "height": 500, "aspect": "3:1"},
        "profile": {"width": 400, "height": 400, "aspect": "1:1"},
        "card": {"width": 1200, "height": 628, "aspect": "1.91:1"},
        "ad": {"width": 1200, "height": 675, "aspect": "16:9"},
    },
    "youtube": {
        "thumbnail": {"width": 1280, "height": 720, "aspect": "16:9"},
        "channel_banner": {"width": 2560, "height": 1440, "aspect": "16:9"},
        "channel_profile": {"width": 800, "height": 800, "aspect": "1:1"},
        "end_screen": {"width": 1280, "height": 720, "aspect": "16:9"},
    },
    "tiktok": {
        "video": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "profile": {"width": 200, "height": 200, "aspect": "1:1"},
    },
    "pinterest": {
        "pin": {"width": 1000, "height": 1500, "aspect": "2:3"},
        "pin_square": {"width": 1000, "height": 1000, "aspect": "1:1"},
        "board_cover": {"width": 222, "height": 150, "aspect": "3:2"},
        "profile": {"width": 165, "height": 165, "aspect": "1:1"},
    },
    "whatsapp": {
        "status": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "profile": {"width": 500, "height": 500, "aspect": "1:1"},
    },
    "telegram": {
        "sticker": {"width": 512, "height": 512, "aspect": "1:1"},
        "channel_photo": {"width": 640, "height": 640, "aspect": "1:1"},
    },
    "snapchat": {
        "snap": {"width": 1080, "height": 1920, "aspect": "9:16"},
        "ad": {"width": 1080, "height": 1920, "aspect": "9:16"},
    },
    "email": {
        "header": {"width": 600, "height": 200, "aspect": "3:1"},
        "banner": {"width": 600, "height": 300, "aspect": "2:1"},
        "hero": {"width": 600, "height": 400, "aspect": "3:2"},
    },
    "website": {
        "hero": {"width": 1920, "height": 1080, "aspect": "16:9"},
        "og_image": {"width": 1200, "height": 630, "aspect": "1.91:1"},
        "favicon": {"width": 512, "height": 512, "aspect": "1:1"},
        "blog_featured": {"width": 1200, "height": 675, "aspect": "16:9"},
        "product": {"width": 1000, "height": 1000, "aspect": "1:1"},
    },
    "print": {
        "a4": {"width": 2480, "height": 3508, "aspect": "1:1.41"},
        "letter": {"width": 2550, "height": 3300, "aspect": "1:1.29"},
        "business_card": {"width": 1050, "height": 600, "aspect": "1.75:1"},
        "poster_a3": {"width": 3508, "height": 4961, "aspect": "1:1.41"},
        "flyer": {"width": 1275, "height": 1650, "aspect": "1:1.29"},
    },
}


def get_dimensions(platform: str, format: str = "post") -> dict:
    """Get dimensions for a platform + format combo."""
    platform = platform.lower().replace(" ", "_").replace("/", "_")
    dims = SOCIAL_MEDIA_DIMENSIONS.get(platform, {})
    if format in dims:
        return dims[format]
    if dims:
        return list(dims.values())[0]
    return {"width": 1024, "height": 1024, "aspect": "1:1"}


def list_platforms() -> dict:
    """List all supported platforms and their formats."""
    return {
        platform: list(formats.keys())
        for platform, formats in SOCIAL_MEDIA_DIMENSIONS.items()
    }


def get_all_dimensions() -> dict:
    """Get complete dimension reference."""
    return SOCIAL_MEDIA_DIMENSIONS
