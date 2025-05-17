from pydantic import BaseModel, Field, ConfigDict, model_validator


class Config(BaseModel):
    """
    Configuration container for Artineo Kinect pipeline.
    Centralise all parameters (ROI, thresholds, directories, mapping constants, network settings).
    Fields can be overridden via a config dict (e.g., fetched from ArtineoClient).
    """

    # Model configuration (Pydantic v2)
    model_config = ConfigDict(
        extra='ignore',      # ignore unexpected keys
        frozen=True          # make config immutable
    )

    # Region of Interest (ROI)
    roi_x0: int = Field(160, ge=0, description="Left X coordinate of ROI")
    roi_y0: int = Field(130, ge=0, description="Top Y coordinate of ROI")
    roi_x1: int = Field(410, gt=0, description="Right X coordinate of ROI")
    roi_y1: int = Field(300, gt=0, description="Bottom Y coordinate of ROI")

    # Template directory
    template_dir: str = Field(
        "images/templates/", description="Directory containing shape/background templates"
    )

    # Shape matching parameters
    use_matchshapes: bool = Field(
        True, description="Use cv2.matchShapes vs. Hu moments"
    )
    area_threshold: float = Field(
        2000.0, gt=0, description="Area threshold for background vs. shape classification"
    )
    small_area_threshold: float = Field(
        250.0, gt=0, description="Area threshold for small-shape classification"
    )

    # Background profile computation
    n_profile: int = Field(
        10, gt=0, description="Number of samples for profile computation"
    )

    # Display parameters (for debug)
    display_scale: int = Field(
        2, gt=0, description="Scale factor for on-screen debug windows"
    )

    # Depth-to-color mapping
    delta: float = Field(
        30.0, description="Mapping delta for depth frames"
    )
    scale: float = Field(
        738.0 / 30.0, description="Computed scale factor: 738/delta"
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
    stroke_radius_tol: int = Field(
        100, gt=0, description="Tolerance for stroke radius"
    )
    stroke_radius_min: int = Field(
        5, gt=0, description="Minimum stroke radius for detection"
    )
    stroke_size_max : int = Field(
        100, gt=0, description="Maximum stroke size for detection"
    )
    stroke_confirmation_frames: int = Field(
        5, gt=0, description="Number of frames for stroke confirmation"
    )

    # Network / WebSocket client settings
    host: str = Field(
        "localhost", description="Artineo server host"
    )
    port: int = Field(
        8000, ge=0, description="Artineo server port"
    )
    module_id: int = Field(
        4, ge=0, description="Unique module identifier for ArtineoClient"
    )

    # Computed fields (read-only)
    roi_width: int | None = Field(
        None, description="Computed width of ROI"
    )
    roi_height: int | None = Field(
        None, description="Computed height of ROI"
    )

    debug_mode: bool = Field(
        True, description="Enable debug mode for displaying windows and detailed logs"
    )

    bypass_ws: bool = Field(
        False, description="Bypass WebSocket connection for debugging"
    )

    @model_validator(mode='before')
    def _compute_roi_dimensions(cls, values: dict) -> dict:
        """
        Compute roi_width and roi_height before model validation.
        """
        x0 = values.get('roi_x0', cls.model_fields['roi_x0'].default)
        y0 = values.get('roi_y0', cls.model_fields['roi_y0'].default)
        x1 = values.get('roi_x1', cls.model_fields['roi_x1'].default)
        y1 = values.get('roi_y1', cls.model_fields['roi_y1'].default)
        values['roi_width'] = x1 - x0
        values['roi_height'] = y1 - y0
        return values

# Example usage:
# from ArtineoClient import ArtineoClient
# client = ArtineoClient(module_id=4, host="artineo.local", port=8000)
# raw_conf = client.fetch_config()
# config = Config(**raw_conf)
# print(config.roi_width, config.roi_height)
