from agent.vision import VisionAnalyzer


class VisionNode:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer or VisionAnalyzer()

    async def run(self, state: dict, runtime=None) -> dict:
        images = state.get("images", [])
        if not images:
            return {"image_desc": "", "detected_products": [], "images": []}
        result = await self.analyzer.aanalyze(images, state["question"])
        description = result.get("description", "")
        detected_products = result.get("detected_products", [])
        if not description and not detected_products and runtime and runtime.recorder:
            runtime.recorder.record({
                "type": "vision_analysis_empty",
                "reason": result.get("error") or "empty vision analysis",
                "image_count": len(images),
                "scene_type": result.get("scene_type", "other"),
            })
        return {
            "image_desc": description,
            "detected_products": detected_products,
            "images": [],
        }
