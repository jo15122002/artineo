import abc
from typing import Optional


class ChannelSelector(abc.ABC):
    """
    Interface pour la sélection du canal (outil) actif.
    """

    @abc.abstractmethod
    async def get_next_channel(self) -> Optional[str]:
        """
        Renvoie un nouvel identifiant d'outil ('1','2','3','4', ...) si un changement est détecté,
        ou None sinon.
        """
        ...