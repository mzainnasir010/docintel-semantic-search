# Page preprocessing example

The preprocessor makes two passes over a fresh page iterator. The first counts
candidate boundary lines; the second yields cleaned pages one at a time. This
keeps page objects out of a retained full-document list. `page_number` remains
metadata even when a printed page number is removed from the text.

## Before

```text
Developer Guide
Install the package with pip.
Page 1 of 3
```

```text
Developer Guide
Use the command line interface.
Page 2 of 3
```

## After

```text
Install the package with pip.
```

```text
Use the command line interface.
```

The report records `developer guide: 2` and `page # of #: 2` removed lines;
the corresponding `PageContent.page_number` values remain 1 and 2.
