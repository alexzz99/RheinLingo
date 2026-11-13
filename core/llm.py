"""Couche LLM interchangeable.

Interface unique : `generer(prompt, systeme) -> str`.
Le fournisseur (LLM_PROVIDER) et le modèle (LLM_MODEL) viennent de la
configuration : aucun nom de modèle n'est codé en dur.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core import config


class LLMError(Exception):
    """Erreur générique du fournisseur LLM (message lisible par l'utilisateur)."""


class LLMQuotaError(LLMError):
    """Quota ou limite de débit dépassé (HTTP 429)."""


class FournisseurLLM(ABC):
    """Contrat commun à tous les fournisseurs."""

    def __init__(self, modele: str, cle_api: str):
        self.modele = modele
        self.cle_api = cle_api

    @abstractmethod
    def generer(self, prompt: str, systeme: str = "") -> str:
        """Envoie `prompt` (avec une consigne système optionnelle) et retourne le texte."""


class GeminiLLM(FournisseurLLM):
    """Implémentation Google Gemini (SDK google-genai)."""

    def generer(self, prompt: str, systeme: str = "") -> str:
        from google import genai
        from google.genai import errors, types

        try:
            client = genai.Client(api_key=self.cle_api)
            reponse = client.models.generate_content(
                model=self.modele,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=systeme or None),
            )
            return reponse.text or ""
        except errors.APIError as e:
            if getattr(e, "code", None) == 429:
                raise LLMQuotaError(
                    "Quota Gemini atteint. Réessaie dans quelques minutes, "
                    "ou passe sur Claude (LLM_PROVIDER=claude)."
                ) from e
            raise LLMError(f"Erreur Gemini ({getattr(e, 'code', '?')}) : {e}") from e


class ClaudeLLM(FournisseurLLM):
    """Implémentation Anthropic Claude."""

    def generer(self, prompt: str, systeme: str = "") -> str:
        import anthropic

        options = {"system": systeme} if systeme else {}
        try:
            client = anthropic.Anthropic(api_key=self.cle_api)
            reponse = client.messages.create(
                model=self.modele,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                **options,
            )
            return "".join(b.text for b in reponse.content if b.type == "text")
        except anthropic.RateLimitError as e:
            raise LLMQuotaError(
                "Limite de débit Claude atteinte. Réessaie dans un instant, "
                "ou passe sur Gemini (LLM_PROVIDER=gemini)."
            ) from e
        except anthropic.APIError as e:
            raise LLMError(f"Erreur Claude : {e}") from e


# Fournisseur -> (classe, nom de la variable contenant la clé API)
_FOURNISSEURS = {
    "gemini": (GeminiLLM, "GEMINI_API_KEY"),
    "claude": (ClaudeLLM, "ANTHROPIC_API_KEY"),
}


def obtenir_llm() -> FournisseurLLM:
    """Construit le fournisseur choisi par LLM_PROVIDER / LLM_MODEL."""
    fournisseur = config.lire("LLM_PROVIDER").lower()
    if fournisseur not in _FOURNISSEURS:
        raise config.ConfigManquante(
            f"LLM_PROVIDER « {fournisseur} » inconnu. Valeurs possibles : "
            + ", ".join(_FOURNISSEURS)
        )
    classe, nom_cle = _FOURNISSEURS[fournisseur]
    return classe(modele=config.lire("LLM_MODEL"), cle_api=config.lire(nom_cle))
