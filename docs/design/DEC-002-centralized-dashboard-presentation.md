# DEC-002: Centralized Dashboard Presentation Configuration

## Status

Accepted for MVP requirements.

## Context

The Streamlit dashboard needs configurable colors and layout so the public demo can be styled or rearranged without scattering hardcoded values across dashboard pages. The user requested that the color scheme be easily changed and that layout also be centrally modifiable.

## Decision

Dashboard color scheme and layout shall be controlled through centralized presentation configuration.

The color configuration shall define semantic tokens for stable, warning, faulty, neutral, background, text, accent, and disabled states. The layout configuration shall define dashboard section order, visibility, grouping, and display density. Individual dashboard pages shall consume these tokens and layout profiles rather than hardcoding colors and layout decisions locally.

## Options Considered

| Option | Pros | Cons |
|---|---|---|
| Hardcode colors and layout in each Streamlit page | Fastest initial implementation. | Hard to maintain; inconsistent styling; changes require editing multiple pages. |
| Single centralized theme file only | Easy color changes. | Does not solve layout changes. |
| Centralized presentation configuration for theme and layout | Consistent styling; easier demo branding; layout can evolve independently. | Requires a small configuration-loading contract and verification. |

## Consequences

- Requirements now include centralized theme and layout configuration.
- API requirements now include a dashboard presentation configuration endpoint.
- Streamlit requirements now include consuming theme tokens and layout profiles.
- Observability requirements now include logging the active theme and layout profile.
- Verification requirements now include proving centralized color and layout loading.

## Related Requirements

- SL-API-021
- SL-UI-030 through SL-UI-034
- SL-OBS-017
- SL-VER-019
