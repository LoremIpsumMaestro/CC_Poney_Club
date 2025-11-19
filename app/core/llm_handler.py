"""
Gestionnaire LLM avec Qwen2.5:14b via Ollama
"""

from typing import AsyncGenerator, Dict, List, Optional

import httpx

from app.config.prompts import SYSTEM_PROMPT
from app.config.settings import settings
from app.utils.logger import log_llm_request, logger


class LLMHandler:
    """
    Gère les interactions avec le LLM (Qwen2.5)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialise le gestionnaire LLM

        Args:
            model_name: Nom du modèle (défaut: depuis settings)
            base_url: URL de l'API Ollama (défaut: depuis settings)
            temperature: Température de génération
            max_tokens: Nombre max de tokens
        """
        self.model_name = model_name or settings.llm_model_name
        self.base_url = base_url or settings.llm_base_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens

        self.client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"Initialisation LLMHandler - Model: {self.model_name} - "
            f"Temperature: {self.temperature} - MaxTokens: {self.max_tokens}"
        )

    async def initialize(self):
        """Initialise le client HTTP"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url, timeout=120.0  # Timeout long pour LLM
            )
            logger.info(f"Client LLM initialisé : {self.base_url}")

            # Vérifier que le modèle est disponible
            await self._check_model_availability()

        except Exception as e:
            logger.error(f"Erreur initialisation LLM: {e}")
            raise

    async def _check_model_availability(self):
        """Vérifie que le modèle est disponible dans Ollama"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [model["name"] for model in data.get("models", [])]

            if self.model_name not in models:
                logger.warning(
                    f"Modèle {self.model_name} non trouvé. Modèles disponibles: {models}"
                )
            else:
                logger.info(f"Modèle {self.model_name} confirmé disponible")

        except Exception as e:
            logger.warning(f"Impossible de vérifier les modèles disponibles: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Génère une réponse du LLM

        Args:
            prompt: Prompt utilisateur
            system_prompt: Prompt système (défaut: SYSTEM_PROMPT)
            temperature: Override température
            max_tokens: Override max tokens
            stream: Mode streaming (non implémenté ici, voir generate_stream)

        Returns:
            Réponse du LLM
        """
        if self.client is None:
            await self.initialize()

        system_prompt = system_prompt or SYSTEM_PROMPT
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        try:
            # Construire les messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            # Requête à Ollama
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            logger.debug(f"Envoi requête LLM - Prompt length: {len(prompt)} chars")

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data["message"]["content"]

            logger.info(f"Réponse LLM reçue - Length: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"Erreur génération LLM: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Génère une réponse en mode streaming

        Args:
            prompt: Prompt utilisateur
            system_prompt: Prompt système
            temperature: Override température
            max_tokens: Override max tokens

        Yields:
            Chunks de texte au fur et à mesure
        """
        if self.client is None:
            await self.initialize()

        system_prompt = system_prompt or SYSTEM_PROMPT
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            async with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        import json

                        data = json.loads(line)

                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content

                        # Vérifier si c'est le dernier message
                        if data.get("done", False):
                            break

        except Exception as e:
            logger.error(f"Erreur streaming LLM: {e}")
            raise

    async def generate_with_context(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Génère une réponse avec contexte RAG

        Args:
            query: Question utilisateur
            context: Contexte récupéré depuis vector stores
            history: Historique de conversation
            system_prompt: Prompt système

        Returns:
            Réponse du LLM
        """
        # Construire le prompt avec contexte
        prompt_parts = []

        if context:
            prompt_parts.append(f"Contexte juridique disponible :\n{context}\n")

        if history:
            prompt_parts.append("Historique de conversation :")
            for msg in history[-5:]:  # Garder les 5 derniers messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")

        prompt_parts.append(f"Question de l'utilisateur :\n{query}")

        full_prompt = "\n".join(prompt_parts)

        return await self.generate(prompt=full_prompt, system_prompt=system_prompt)

    async def close(self):
        """Ferme le client HTTP"""
        if self.client:
            await self.client.aclose()
            logger.info("Client LLM fermé")


# Instance globale (singleton)
_llm_handler: Optional[LLMHandler] = None


async def get_llm_handler() -> LLMHandler:
    """
    Récupère l'instance globale du gestionnaire LLM

    Returns:
        Instance initialisée de LLMHandler
    """
    global _llm_handler

    if _llm_handler is None:
        _llm_handler = LLMHandler()
        await _llm_handler.initialize()

    return _llm_handler


__all__ = ["LLMHandler", "get_llm_handler"]
