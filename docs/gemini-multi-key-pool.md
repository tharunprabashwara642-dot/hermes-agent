# Gemini Multi-Key Credential Pool

Hermes already has a provider credential pool with same-provider rotation and rate-limit recovery. This repository's Gemini provider now exposes a large numbered environment-variable range so Gemini API keys can be supplied without putting the raw keys into the repository.

## Environment variables

Use the primary variable plus numbered siblings:

```dotenv
GEMINI_API_KEY=your-first-key
GEMINI_API_KEY_2=your-second-key
GEMINI_API_KEY_3=your-third-key
GEMINI_API_KEY_4=your-fourth-key
```

The historical Google alias is also supported:

```dotenv
GOOGLE_API_KEY=your-first-key
GOOGLE_API_KEY_2=your-second-key
GOOGLE_API_KEY_3=your-third-key
```

Do not commit real keys to Git.

## Rotation strategy

Set this in `~/.hermes/config.yaml`:

```yaml
credential_pool_strategies:
  gemini: round_robin
```

`round_robin` causes healthy pool credentials to be selected in order. Hermes persists the pool ordering, so a new process/turn continues from the next credential instead of always starting from the first key.

## Limit recovery

The existing credential-pool error path handles provider failures. When a key is rate-limited or its quota/billing limit is exhausted, Hermes can mark that credential unavailable and select another healthy Gemini credential. The task can therefore continue on another key instead of stopping immediately.

## Model selection

Key pooling is independent of model selection. Keep using Hermes model configuration or the normal `--model`/`hermes model` workflow to choose the Gemini model you want. All Gemini API keys in the pool can serve the selected model.

## More than the numbered range

The provider exposes `GEMINI_API_KEY` plus `GEMINI_API_KEY_2` through `GEMINI_API_KEY_256` (and the equivalent `GOOGLE_API_KEY` names). For additional credentials beyond that range, use Hermes' existing pool command:

```bash
hermes auth add gemini --type api-key --api-key YOUR_KEY
```

Those manually-added credentials join the same Gemini pool and rotation strategy.
