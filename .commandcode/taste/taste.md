# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# Architecture
- Merge API layers into DRF class-based views. Consolidate legacy function-based views into a single DRF app and delete the old codebase. Confidence: 0.70

# Design
- Use black/dark themes instead of reddish/orange color schemes. The orange-accent theme looks bad — prefer neutral black backgrounds with subtle accents. Confidence: 0.80

# Performance
- Avoid custom cursors — use the default browser cursor. Custom cursors add unnecessary overhead and feel unnatural. Confidence: 0.70
- Keep pages lightweight and smooth — avoid heavy GSAP/Lenis/ScrollTrigger, canvas particle systems, and multiple parallax effects that cause lag. Prioritize performance over flashy animations. Confidence: 0.70
