# Native Layer Notes

This directory is reserved for the future native binding layer.

Current boundaries:

- Prefer upstream public headers only:
  - `libvgmstream.h`
  - `libvgmstream_streamfile.h`
- Keep the binding cross-platform.
- Do not hardcode Windows-only path logic, DLL names, or executable assumptions.
- `.wem` is the primary validation target, but the architecture must allow other
  formats to work naturally when upstream public APIs support them without
  extra adaptation cost.
- Real native targets are intentionally deferred until the Python package shell,
  test entrypoints, and project conventions are stable.
