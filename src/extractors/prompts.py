"""Prompt templates for vision model."""

PAPER_EXTRACTION_PROMPT = """You are analyzing a research paper poster from a conference. 
Extract the following information and return it as a VALID JSON object.

CRITICAL RULES:
1. Return ONLY a valid JSON object, nothing else
2. Use double quotes for strings, not single quotes
3. Do NOT include line breaks within string values
4. Do NOT include comments in the JSON
5. If a field is not visible, use null (not "null", not empty string)
6. For array fields, use [] if empty, never use null

Required JSON format:
{
  "title": "paper title here",
  "authors": ["author1 name", "author2 name"],
  "overview": "brief overview of what the paper is about - what problem it solves, techniques used, and key results shown. Only include information visible in the image. 2-3 sentences maximum. no line breaks"
}

Rules for each field:
- title: string, use "Unknown" if not visible
- authors: array of author names (just names, no emails or affiliations), use [] if not visible
- overview: string (one line, no line breaks) or null

Example output:
{
  "title": "Deep Learning for Image Classification",
  "authors": ["John Smith", "Jane Doe"],
  "overview": "The paper is about the problem of image classification using deep learning that achieves state-of-the-art results."
}

Now analyze this poster and return ONLY the JSON object:"""


PAPER_EXTRACTION_PROMPT_SIMPLE = """Extract information from this conference poster. Return ONLY valid JSON with this structure:

{
  "title": "paper title",
  "authors": ["name1", "name2"],
  "overview": "summary text"
}

Rules:
- Use [] for empty authors array, never null
- Use null for missing title or overview
- No line breaks in strings
- Return ONLY JSON, no other text

JSON only:"""

CONFERENCE_SUMMARY_PROMPT = """Analyze these research paper titles and overviews from a conference and provide a concise summary.

Provide a summary (300-500 words) covering main themes, and technologies in a single paragraph:
1. Main Theme: What are the dominant research areas or topics?
2. Key Technologies: What methods, models, or frameworks are trending?

Be specific and insightful. Use technical language appropriate for researchers.

Papers:
{papers_text}

"""


def get_extraction_prompt(use_simple: bool = False) -> str:
    """
    Get the prompt template for paper extraction.
    
    Args:
        use_simple: If True, use simplified prompt
        
    Returns:
        Prompt string
    """
    return PAPER_EXTRACTION_PROMPT_SIMPLE if use_simple else PAPER_EXTRACTION_PROMPT