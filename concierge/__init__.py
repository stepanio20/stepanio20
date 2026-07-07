"""Concierge layer — recommendation + orchestration on top of the Knowledge Engine.

See ../PRODUCT_ARCHITECTURE.md. Pure-stdlib, no third-party dependencies, so it
runs anywhere the pipeline does.
"""
__all__ = ["recommend", "orchestrate"]
