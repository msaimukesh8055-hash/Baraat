"""Baraat extraction (Track B): turn messy vendor prose into validated JSON records.

This is the structured-output-reliability layer (competency #7). It is SEPARATE
from retrieval/RAG (Track A): the records produced here exist so downstream tools
can do math and comparison, not to feed the retriever.
"""
