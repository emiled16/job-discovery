---
name: career-website-consolidator
description: Explain how to create adatapters to consolidate results from agents who explore company career websites in order to extract job listings. Use when asked to create adapters for job listing extraction from company career pages.
---

# Career Website Explorer
You have access to agents who can explore company career websites, extract job listings, and provide structured data about them.

Using their exploration result, do the following:

- Identify the main career websites platforms (e.g., Greenhouse, Lever, Workday) and custom-built sites.
- If the company has a known platform, create an adapter to extract job listings from that platform if it doesnt exist. (see @/Users/emdim/dev/job-discovery/backend/src/job_discovery_backend/ingestion/adapters)
- If the company has a custom-built site, create a generic HTML adapter to extract job listings. You can use tools like BeautifulSoup, Selenium, or curl-cffi (call the apis endpoint directly if they exist) to fetch and parse the HTML content.
- If the company has a bot detection mechanism, just skip it and mark it as "unsupported" for now. We can explore solutions for bot detection in the future.
- Normalize the extracted job data into a consistent format (follow what has already been implemented)


There is also a way to create our own langchain agent, but this is expensive. I would prioritize having adapters to the most common platforms.

Document the result inside docs/