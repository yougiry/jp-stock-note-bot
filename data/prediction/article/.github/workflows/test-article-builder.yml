name: Test v5.11 article builder

on:
  workflow_dispatch:

jobs:
  build-article:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build note article
        run: python article/article_builder.py

      - name: Show generated article
        run: cat output/note_article.html
