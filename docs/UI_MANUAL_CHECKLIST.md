# Quillseek UI manual verification

Use the two-terminal launch flow in the README, then open `http://127.0.0.1:7860`.

## Visual and interaction checks

- [ ] The browser tab title is **Quillseek** and the Quillseek favicon appears.
- [ ] The header logo and footer logo are visible and readable.
- [ ] Documents, Search, and Ask tabs fit at desktop width and at a narrow mobile width (around 375 px); no horizontal page overflow.
- [ ] The header, cards, controls, and footer have consistent spacing and readable text.
- [ ] Primary buttons have visible hover and keyboard focus states; inputs and expandable source cards can be focused and used by keyboard.
- [ ] Pink accents (score pills and focus rings) use deep-blue text/outline; white text appears on deep-blue surfaces. Do not use white text directly on pink.
- [ ] Reduced-motion preference disables animated/transitional movement.
- [ ] Upload and index a small supported document, search for a phrase in it, then ask a question. Verify source and page details.
- [ ] Check browser developer console for errors during the above flow.

## Screenshots requested for Step 10.2

Capture each UI state as a separate PNG in `docs/screenshots/`, using these filenames:

1. `01-documents-indexed.png` — Documents tab showing indexed sample documents.
2. `02-indexing-progress.png` — Documents tab while indexing, with visible progress.
3. `03-search-results-scores.png` — Search results showing ranked passages and similarity scores.
4. `04-answer-with-sources.png` — Ask tab showing a successful answer and its source cards.
5. `05-refusal.png` — Ask tab showing a refusal for a question the corpus cannot answer.
6. `06-empty-state.png` — Documents tab before any document has been uploaded.

Keep sample content free of personal or confidential data. A narrow-width screenshot is also useful for responsive review, but is additional to these six requested states.
