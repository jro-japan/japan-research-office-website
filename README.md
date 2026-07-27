{
  "ci": {
    "collect": {
      "staticDistDir": ".",
      "url": [
        "http://localhost/",
        "http://localhost/services.html",
        "http://localhost/pricing.html",
        "http://localhost/contact.html"
      ],
      "numberOfRuns": 1,
      "settings": {
        "preset": "desktop",
        "chromeFlags": "--no-sandbox"
      }
    },
    "assert": {
      "assertions": {
        "categories:performance": [
          "error",
          {
            "minScore": 0.85
          }
        ],
        "categories:accessibility": [
          "error",
          {
            "minScore": 0.95
          }
        ],
        "categories:best-practices": [
          "error",
          {
            "minScore": 0.95
          }
        ],
        "categories:seo": [
          "error",
          {
            "minScore": 0.95
          }
        ]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}