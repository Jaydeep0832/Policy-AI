import re
from typing import List, Dict, Any, Optional
from app.models import CitedChunk, VerifiedCitation

def normalize_text(text: str) -> str:
    """Normalize text by stripping soft hyphens, special unicode quotes, and collapsing whitespace."""
    if not text:
        return ""
    text = text.replace('\xad', '')  # Soft hyphen
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

class CitationVerifier:
    def __init__(self, chunk_lookup: Dict[str, Dict[str, Any]]):
        self.chunk_lookup = chunk_lookup

    def verify_citations(
        self,
        raw_citations: List[CitedChunk],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> List[VerifiedCitation]:
        """Validates quotes against retrieved chunks and binds authoritative metadata."""
        verified_list: List[VerifiedCitation] = []
        retrieved_ids = {c["chunk_id"]: c for c in retrieved_chunks}

        for cite in raw_citations:
            target_chunk = self.chunk_lookup.get(cite.chunk_id) or retrieved_ids.get(cite.chunk_id)
            
            # If chunk_id wasn't an exact match, try matching from retrieved chunks by snippet containment
            if not target_chunk:
                norm_quote = normalize_text(cite.quoted_snippet)
                for c in retrieved_chunks:
                    if norm_quote and norm_quote in normalize_text(c["text"]):
                        target_chunk = c
                        break

            if target_chunk:
                norm_chunk = normalize_text(target_chunk["text"])
                norm_quote = normalize_text(cite.quoted_snippet)

                # Check verbatim substring containment
                is_contained = bool(norm_quote and (norm_quote in norm_chunk))

                # Fallback: token set overlap for minor token variations
                if not is_contained and norm_quote:
                    quote_tokens = set(norm_quote.split())
                    chunk_tokens = set(norm_chunk.split())
                    if len(quote_tokens) > 0 and len(quote_tokens.intersection(chunk_tokens)) / len(quote_tokens) >= 0.85:
                        is_contained = True

                verified_list.append(VerifiedCitation(
                    chunk_id=target_chunk["chunk_id"],
                    document=target_chunk["document_title"],
                    version=target_chunk["version"],
                    page_number=target_chunk["page_number"],
                    section=target_chunk.get("breadcrumb", target_chunk["document_title"]),
                    quoted_snippet=cite.quoted_snippet,
                    verified_in_source=is_contained
                ))
            else:
                # If chunk could not be matched at all, flag with fallback
                verified_list.append(VerifiedCitation(
                    chunk_id=cite.chunk_id,
                    document="Unknown Document",
                    version="Unknown",
                    page_number=1,
                    section="General",
                    quoted_snippet=cite.quoted_snippet,
                    verified_in_source=False
                ))

        return verified_list
