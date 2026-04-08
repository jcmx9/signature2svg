"""Pipeline configuration with Pydantic validation."""

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Configuration for the signature vectorization pipeline."""

    turdsize: int = Field(default=2, ge=0, description="Suppress speckles smaller than N px")
    alphamax: float = Field(default=1.0, ge=0.0, le=1.3, description="Corner smoothing (0.0–1.3)")
    opttolerance: float = Field(default=0.2, ge=0.0, description="Curve optimization tolerance")
    blur: int = Field(default=3, ge=0, description="Median blur kernel size (0 = off)")
    morph: int = Field(default=2, ge=0, description="Morphological closing kernel size (0 = off)")
    debug: bool = Field(default=False, description="Write intermediate images to output dir")
