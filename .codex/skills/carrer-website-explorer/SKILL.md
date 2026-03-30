---
name: career-website-explorer
description: Explain what to do to explore the company career websites in order to extract job listings. Use when asked to research and explore company career websites to extract job listings.
---
# Career Website Explorer
Open the given company career website and explore it structure in the following way:

- If the company uses a known career website platform (e.g., Greenhouse, Lever, Workday), return the platform name and the URL of the career page.
- If the company has a custom-built career website, do the following:
  - If the company has a bot detection mechanism, just skip it and mark it as "unsupported" for now. We can explore solutions for bot detection in the future.
  - Else, if the company has a usable api endpoint, understand the api structure and return the necessary endpoint and the data format.
  - Else, if the company has a usable HTML structure, return the necessary information to create a generic HTML adapter to extract job listings. 


Document the result inside docs/