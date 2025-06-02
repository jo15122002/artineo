from pydantic import BaseModel, Field, ConfigDict, model_validator


class Config(BaseModel):
    """
    Configuration container for Artineo Kinect pipeline.
    Centralise all parameters (ROI, thresholds, directories, mapping constants, network settings).
    """

    # Pydantic v2 settings
    model_config = ConfigDict(
        extra="ignore",    # ignore unexpected keys
        frozen=True        # make config immutable
    )

    # ─────────── ROI SIZE ────────────
    roi_x0: int = Field(125, ge=0, description="Left X coordinate of ROI")
    roi_y0: int = Field(90, ge=0, description="Top Y coordinate of ROI")
    roi_x1: int = Field(400, gt=0, description="Right X coordinate of ROI")
    roi_y1: int = Field(265, gt=0, description="Bottom Y coordinate of ROI")

    # ───────── Templates ─────────
    template_dir: str = Field(
        "templates/", description="Directory containing shape/background templates"
    )

    # ─── Shape matching thresholds ───
    use_matchshapes: bool = Field(
        True, description="Use cv2.matchShapes vs. Hu moments"
    )
    area_threshold: float = Field(
        15000.0, gt=0, description="Area threshold for background vs. shape classification"
    )
    small_area_threshold: float = Field(
        500.0, gt=0, description="Area threshold for small-shape classification"
    )
    removal_threshold: float = Field(
        2.0, gt=0, description="Area threshold for removing small shapes"
    )
    removal_ratio: float = Field(
        0.2, ge=0.0, le=1.0, description="Ratio of pixels above removal_threshold to remove shape"
    )
    match_threshold: float = Field(
        100.0, gt=0, description="Maximum MSE threshold for shape matching"
    )

    # ─── Background profiling ───
    n_profile: int = Field(
        10, gt=0, description="Number of samples for profile computation"
    )

    # ─── Depth→color mapping ───
    scale: float = Field(
        738.0 / 30.0, description="Computed scale factor (738/delta)"
    )
    alpha: float = Field(
        0.1, ge=0.0, le=1.0, description="Exponential smoothing factor for brush accumulation"
    )
    brush_scale: float = Field(
        1.2, gt=0, description="Scale multiplier for brush stroke size"
    )
    stroke_intensity_thresh: int = Field(
        30, gt=0, description="Threshold for stroke intensity"
    )
    stroke_radius_min: int = Field(
        5, gt=0, description="Minimum stroke radius for detection"
    )
    stroke_size_max: float = Field(
        100.0, gt=0, description="Maximum stroke size for detection"
    )
    stroke_confirmation_frames: int = Field(
        5, gt=0, description="Number of consecutive frames for stroke confirmation"
    )

    # ─── Network / WS client ───
    host: str = Field("localhost", description="Artineo server host")
    port: int = Field(8000, ge=0, description="Artineo server port")
    module_id: int = Field(4, ge=0, description="Unique module identifier for ArtineoClient")

    # ─── Computed read-only fields ───
    roi_width: int | None = Field(None, description="Computed width of ROI")
    roi_height: int | None = Field(None, description="Computed height of ROI")
    calibrate_roi: bool = Field(
        False, description="If true, add a window to calibrate ROI dimensions"
    )

    # ─── Mode debug / bypass WS ───
    debug_mode: bool = Field(
        True, description="Enable debug windows and verbose logging"
    )
    bypass_ws: bool = Field(
        False, description="If true, do not open WebSocket (for offline debug)"
    )
    
    # ─── Display (debug) ───
    display_scale: int = Field(
        2, gt=0, description="Scale factor for on-screen debug windows"
    )

    @model_validator(mode="before")
    def _compute_roi_dimensions(cls, values: dict) -> dict:
        """
        Compute roi_width and roi_height before validation.
        """
        x0 = values.get("roi_x0", cls.model_fields["roi_x0"].default)
        y0 = values.get("roi_y0", cls.model_fields["roi_y0"].default)
        x1 = values.get("roi_x1", cls.model_fields["roi_x1"].default)
        y1 = values.get("roi_y1", cls.model_fields["roi_y1"].default)
        values["roi_width"] = x1 - x0
        values["roi_height"] = y1 - y0
        return values
