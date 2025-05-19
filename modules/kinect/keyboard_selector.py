import cv2
from typing import Optional
from channel_selector import ChannelSelector


class KeyboardChannelSelector(ChannelSelector):
    """
    Sélectionne le canal via les touches '1','2','3','4' du pavé numérique.
    """

    VALID_KEYS = {
        ord('1'): '1',
        ord('2'): '2',
        ord('3'): '3',
        ord('4'): '4',
    }

    async def get_next_channel(self) -> Optional[str]:
        key = cv2.waitKey(1) & 0xFF
        return self.VALID_KEYS.get(key)