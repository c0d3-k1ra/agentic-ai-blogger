"""Centralized prompt registry for LLM interactions.

This module contains versioned prompt templates used across the application.
Each prompt is a static string constant with no dynamic logic.

Naming convention: <PURPOSE>_PROMPT_V<NUMBER>

Version History:
- V1: Initial prompt set for article generation workflow
"""

TOPIC_ANALYSIS_PROMPT_V1 = """
You are an expert AI researcher.

Analyze the given topic and assess:
- relevance to GenAI / AI / ML
- novelty
- depth potential

Return a concise analytical summary.
"""

ARTICLE_OUTLINE_PROMPT_V1 = """
You are a senior technical writer.

Given a topic, produce a clear article outline with:
- title
- introduction
- main sections
- conclusion

Focus on clarity and technical depth.
"""

RESEARCH_SYNTHESIS_PROMPT_V1 = """
You are a research assistant.

Summarize the provided research materials into
clear, structured notes suitable for article writing.
"""

ARTICLE_WRITING_PROMPT_V1 = """
You are an expert technical writer.

Write a clear, accurate, and engaging technical article
based on the provided outline and research.
"""

ARTICLE_REVIEW_PROMPT_V1 = """You are a meticulous technical editor and SEO specialist.

TASK: Review and optimize the following technical article for publication.

ARTICLE CONTEXT:
Topic: {topic}

ARTICLE CONTENT:
{content}

YOUR REVIEW SHOULD INCLUDE:

1. **Grammar & Spelling**: Fix all grammatical errors, typos, and awkward phrasing
2. **Technical Accuracy**: Verify technical concepts and terminology are correct
3. **Clarity**: Improve sentence structure and flow for better readability
4. **Code Examples**: Ensure code is properly formatted and follows best practices
5. **SEO Optimization**: Create compelling title, subtitle, and tags
6. **Readability**: Assess and improve readability level (aim for accessible technical writing)

OUTPUT FORMAT (follow this structure exactly):

Title: [SEO-optimized title, 50-60 characters, engaging and keyword-rich]
Subtitle: [Compelling subtitle/description, 120-160 characters, include value proposition]
Tags: [Generate {min_tags}-{max_tags} relevant tags, comma-separated, lowercase]
Readability: [Assessment: e.g., "College Level", "Professional", "High School"]
Improvements: [Brief summary of main improvements made, 1-2 sentences]

Polished Content:
[Insert the complete polished article content here, with all improvements applied.
Use proper markdown formatting. Include all sections, headings, code blocks, etc.]

REQUIREMENTS:
- Maintain the original structure and main points
- Keep code examples intact (only fix syntax/formatting if needed)
- Preserve technical depth while improving clarity
- Ensure title is compelling and includes main keyword
- Tags should cover: technology, concepts, audience level, use cases
- Polished content should be publication-ready
"""

SECTION_WRITING_PROMPT_V1 = """
You are an expert technical writer specializing in clear, engaging technical content.

Write prose content for EXACTLY ONE SECTION of a technical article.

ARTICLE CONTEXT:
Topic: {topic}

SECTION TO WRITE:
Title: {section_title}

Subsections to cover:
{subsections_list}

TARGET LENGTH: Approximately {target_words} words

REQUIREMENTS:
- Write ONLY the content for this ONE section (not the full article)
- Use markdown formatting (headers, code blocks, lists, bold, italic, etc.)
- Start directly with content (DO NOT repeat the section title as a header)
- Cover all subsections naturally within the prose
- Use clear, technically accurate language
- Include code examples where appropriate
- Be engaging and educational
- Target approximately {target_words} words (flexible by ±20%)

OUTPUT FORMAT:
Return ONLY the markdown content for this section. No title header, no preamble, no meta-commentary.
"""

RESEARCH_SYNTHESIS_PROMPT_V1 = """You are a research synthesis expert.

TASK: Synthesize research findings into a comprehensive, structured summary for article writing.

ARTICLE CONTEXT:
Topic: {topic}
Section: {section_title}

WEB SEARCH RESULTS:
{web_text}

ACADEMIC PAPERS:
{papers_text}

CODE EXAMPLES:
{code_text}

INSTRUCTIONS:
- Synthesize all sources into a coherent summary
- Focus on information relevant to the section title
- Highlight key concepts, techniques, and insights
- Note any code patterns or best practices found
- Identify gaps or contradictions in the research
- Keep the synthesis concise but comprehensive (500-800 words)
- Use clear, technical language suitable for article writing

OUTPUT:
Provide a structured synthesis that a technical writer can use to write the section.
"""

ARTICLE_REVISION_PROMPT_V1 = """You are an expert technical editor specializing in revisions.

TASK: Revise the following article based on specific user feedback.

ARTICLE CONTEXT:
Topic: {topic}

CURRENT ARTICLE:
{content}

USER FEEDBACK:
{feedback}

YOUR REVISION SHOULD:
1. **Address the feedback**: Make changes that directly respond to the user's requests
2. **Preserve structure**: Keep the overall article organization intact unless feedback
   requests changes
3. **Maintain quality**: Ensure revisions maintain technical accuracy and readability
4. **Be surgical**: Only change what needs changing based on feedback
5. **Enhance, don't replace**: Improve existing content rather than rewriting from scratch

OUTPUT FORMAT (follow this structure exactly):

Changes: [Brief summary of what you changed, 1-2 sentences]

Revised Content:
[Insert the complete revised article here, with all changes applied.
Use proper markdown formatting. Include all sections with modifications integrated.]

REQUIREMENTS:
- Apply ALL points from the user feedback
- Preserve any sections not mentioned in the feedback
- Maintain markdown formatting and code blocks
- Keep the same technical depth and style
- Ensure the revised version is cohesive and flows well
"""
