"""
Módulo de extração de PDFs de decisões do STF usando Docling.

Foca na extração de alta qualidade das seções 'Voto' e 'Dispositivo',
seguindo os princípios de Context Engineering do QuaLLM-KG.
"""

from __future__ import annotations

import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from src.models.schemas import ExtractionResult


def _build_converter() -> DocumentConverter:
    """Cria o DocumentConverter com OCR habilitado para macOS (português)."""
    ocr_options = OcrMacOptions(
        lang=["pt-BR", "en-US"],
        force_full_page_ocr=True,
    )
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=ocr_options,
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def _extract_section(text: str, section_name: str) -> str:
    """Extrai uma seção específica do texto do acórdão.

    Tenta múltiplos padrões de regex para capturar variações de formatação
    encontradas em acórdãos do STF.
    """
    patterns = [
        # Padrão 1: "V O T O" ou "VOTO" seguido de conteúdo até próxima seção
        rf"(?:^|\n)\s*{section_name}[\s\n]+(.*?)(?=\n\s*(?:DISPOSITIVO|EMENTA|ACÓRDÃO|RELATÓRIO|EXTRATO\s+DE\s+ATA|$))",
        # Padrão 2: Seção com separador (traços, asteriscos)
        rf"(?:^|\n)\s*[-*=]*\s*{section_name}\s*[-*=]*\s*\n(.*?)(?=\n\s*[-*=]*\s*(?:DISPOSITIVO|EMENTA|ACÓRDÃO|RELATÓRIO|$))",
        # Padrão 3: Seção entre marcadores de página
        rf"{section_name}\s*\n(.*?)(?=(?:DISPOSITIVO|EMENTA|ACÓRDÃO|RELATÓRIO|\Z))",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            extracted = match.group(1).strip()
            # Limpa artefatos de OCR e formatação
            extracted = re.sub(r"\n{3,}", "\n\n", extracted)
            extracted = re.sub(r"[ \t]{2,}", " ", extracted)
            return extracted

    return ""


def _clean_text(text: str) -> str:
    """Remove artefatos comuns de extração de PDF."""
    # Remove cabeçalhos/rodapés repetidos do STF
    text = re.sub(
        r"SUPREMO TRIBUNAL FEDERAL.*?(?=\n)", "", text, flags=re.IGNORECASE
    )
    # Remove números de página isolados
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    # Normaliza espaçamento
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_from_pdf(pdf_path: str | Path) -> ExtractionResult:
    """Extrai texto de um PDF de decisão do STF usando Docling.

    Args:
        pdf_path: Caminho para o arquivo PDF.

    Returns:
        ExtractionResult com texto completo, voto e dispositivo extraídos.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    converter = _build_converter()
    result = converter.convert(str(pdf_path))

    full_text = result.document.export_to_markdown()
    full_text = _clean_text(full_text)

    voto = _extract_section(full_text, "V\\s*O\\s*T\\s*O")
    if not voto:
        voto = _extract_section(full_text, "VOTO")

    dispositivo = _extract_section(full_text, "D\\s*I\\s*S\\s*P\\s*O\\s*S\\s*I\\s*T\\s*I\\s*V\\s*O")
    if not dispositivo:
        dispositivo = _extract_section(full_text, "DISPOSITIVO")

    return ExtractionResult(
        arquivo=pdf_path.name,
        texto_completo=full_text,
        voto=voto,
        dispositivo=dispositivo,
        metadata={
            "paginas": len(full_text) // 3000 + 1,  # estimativa
            "tamanho_chars": len(full_text),
            "voto_encontrado": bool(voto),
            "dispositivo_encontrado": bool(dispositivo),
        },
    )


def extract_all_from_directory(directory: str | Path) -> list[ExtractionResult]:
    """Extrai texto de todos os PDFs em um diretório.

    Args:
        directory: Caminho para o diretório contendo PDFs.

    Returns:
        Lista de ExtractionResult, um por PDF.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Diretório não encontrado: {directory}")

    pdf_files = sorted(directory.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Nenhum PDF encontrado em: {directory}")

    results = []
    for pdf_path in pdf_files:
        try:
            result = extract_from_pdf(pdf_path)
            results.append(result)
        except Exception as e:
            print(f"[ERRO] Falha ao processar {pdf_path.name}: {e}")

    return results
