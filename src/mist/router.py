from mist.schemas import ModelConfig, RouterMode, Settings


class Router:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.models = {model.id: model for model in settings.models}

    def select(self, text: str, mode: RouterMode) -> ModelConfig:
        use_primary = mode is RouterMode.PRIMARY
        if mode is RouterMode.AUTO:
            use_primary = len(text) > 600 or any(
                term in text.casefold()
                for term in ("planeje", "arquitetura", "analise", "compare", "passo a passo")
            )
        model_id = self.settings.primary_model if use_primary else self.settings.fast_model
        return self.models[model_id]

