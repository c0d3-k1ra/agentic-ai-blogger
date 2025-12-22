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

ARTICLE_REVIEW_PROMPT_V1 = """
You are a meticulous technical editor.

Review the article for:
- clarity
- correctness
- structure
- readability

Return a refined version of the article.
"""
