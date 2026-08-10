# Build Lab presentation layer

Despite the `preview` directory name, these files are part of the live Build Lab deployment.

`.cpanel.yml` copies `index.html`, the Build Lab CSS files, and `media-enhancements.js` into `$HOME/public_html/build-planner/` after the planner base, v1.3 player corpus, and image pack are installed.

Do not remove this directory while `.cpanel.yml` references it.
