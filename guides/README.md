# guides/

Built in the km-quiz repo (`python3 pipeline/build_pages.py --site <this folder> --only content/launch-1.txt`).
Don't edit by hand; rebuild from km-quiz and replace the folder.

- `ideas/` — business idea guides and the /ideas/ hub, with `<!--KM:NAV-->` / `<!--KM:FOOTER-->` markers
- `quiz/` — the business fit quiz, served at /quiz/ (`?idea=<key>` opens a fit check for one idea)
- `urls.txt` — paths added to sitemap.xml

`build.py` copies this folder into `docs/` when `PUBLISH_IDEA_GUIDES = True`.
