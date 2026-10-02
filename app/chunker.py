import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from app.models import PolicyManifestItem, PolicyChunk

HEADING_PATTERNS = [
    re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE),  # Markdown #, ##, ###
    re.compile(r'^(\(\d+\))\s+([A-Z\s]{3,})$', re.MULTILINE),  # (5) KINDS OF LEAVE
    re.compile(r'^(\d+(?:\.\d+)+)\s+([A-Z\s]{3,}.*)$', re.MULTILINE),  # 5.1 LEAVE TYPE 1: CASUAL LEAVE
    re.compile(r'^(Section|Clause|Article|Chapter)\s+(\d+(?:\.\d+)*)[:\s]*(.*)$', re.IGNORECASE | re.MULTILINE)
]

def clean_text(text: str) -> str:
    """Normalize whitespace and strip soft hyphens from PDF text extraction."""
    text = text.replace('\xad', '')  # Soft hyphen
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_pdf_pages(file_path: Path) -> List[Tuple[int, str]]:
    """Extract page number and raw text pairs from PDF."""
    doc = fitz.open(str(file_path))
    pages = []
    for idx, page in enumerate(doc):
        text = clean_text(page.get_text("text"))
        if text:
            pages.append((idx + 1, text))
    return pages

def extract_markdown_content(file_path: Path) -> List[Tuple[int, str]]:
    """Load markdown file as a single page or split logically."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = clean_text(f.read())
    return [(1, text)]

class HierarchicalPolicyChunker:
    def __init__(self, target_chunk_size: int = 1800, overlap_size: int = 250):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def chunk_document(self, item: PolicyManifestItem, file_path: Path) -> List[PolicyChunk]:
        """Parse document pages and chunk with hierarchical section breadcrumbs."""
        if file_path.suffix.lower() == ".pdf":
            pages = extract_pdf_pages(file_path)
        else:
            pages = extract_markdown_content(file_path)

        chunks: List[PolicyChunk] = []
        current_breadcrumb = item.title
        chunk_idx = 1

        for page_num, page_text in pages:
            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
            buffer = ""

            for para in paragraphs:
                # Check for heading markers to update breadcrumb
                heading_match = None
                for pat in HEADING_PATTERNS:
                    m = pat.search(para)
                    if m:
                        heading_match = m
                        break

                if heading_match:
                    matched_heading = para.split('\n')[0].strip()
                    if len(matched_heading) < 120:
                        current_breadcrumb = f"{item.title} > {matched_heading}"

                if len(buffer) + len(para) + 2 > self.target_chunk_size:
                    if buffer:
                        chunk_id = f"{item.policy_id}_p{page_num}_c{chunk_idx}"
                        header_tag = f"[DOC: {item.title} | BREADCRUMB: {current_breadcrumb} | PAGE: {page_num} | CHUNK_ID: {chunk_id}]\n\n"
                        full_chunk_text = header_tag + buffer

                        chunks.append(PolicyChunk(
                            chunk_id=chunk_id,
                            document_title=item.title,
                            file_name=item.file_name,
                            policy_id=item.policy_id,
                            version=item.version,
                            status=item.status,
                            effective_date=item.effective_date,
                            is_latest=item.is_latest,
                            page_number=page_num,
                            breadcrumb=current_breadcrumb,
                            precedence_rank=item.precedence_rank,
                            text=full_chunk_text,
                            token_count=len(full_chunk_text) // 4
                        ))
                        chunk_idx += 1
                        # Retain overlap from end of buffer
                        buffer = buffer[-self.overlap_size:] + "\n\n" + para if len(buffer) > self.overlap_size else para
                    else:
                        buffer = para
                else:
                    if buffer:
                        buffer += "\n\n" + para
                    else:
                        buffer = para

            if buffer.strip():
                chunk_id = f"{item.policy_id}_p{page_num}_c{chunk_idx}"
                header_tag = f"[DOC: {item.title} | BREADCRUMB: {current_breadcrumb} | PAGE: {page_num} | CHUNK_ID: {chunk_id}]\n\n"
                full_chunk_text = header_tag + buffer.strip()

                chunks.append(PolicyChunk(
                    chunk_id=chunk_id,
                    document_title=item.title,
                    file_name=item.file_name,
                    policy_id=item.policy_id,
                    version=item.version,
                    status=item.status,
                    effective_date=item.effective_date,
                    is_latest=item.is_latest,
                    page_number=page_num,
                    breadcrumb=current_breadcrumb,
                    precedence_rank=item.precedence_rank,
                    text=full_chunk_text,
                    token_count=len(full_chunk_text) // 4
                ))
                chunk_idx += 1

        return chunks
