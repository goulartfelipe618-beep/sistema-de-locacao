"""Formatação de endereço de filial para exibição e geocodificação."""

from __future__ import annotations

from app.modules.tenants.models import Filial


def format_filial_address(filial: Filial) -> str | None:
    parts: list[str] = []
    street = (filial.address or "").strip()
    number = (filial.number or "").strip()
    if street:
        parts.append(f"{street}{', ' + number if number else ''}")
    district = (filial.district or "").strip()
    if district:
        parts.append(district)
    city = (filial.city or "").strip()
    state = (filial.state or "").strip()
    if city and state:
        parts.append(f"{city} — {state}")
    elif city:
        parts.append(city)
    zip_code = (filial.zip_code or "").strip()
    if zip_code and len(zip_code) == 8:
        parts.append(f"CEP {zip_code[:5]}-{zip_code[5:]}")
    if not parts:
        return None
    return ", ".join(parts)


def filial_public_row(filial: Filial) -> dict:
    lat = float(filial.latitude) if filial.latitude is not None else None
    lng = float(filial.longitude) if filial.longitude is not None else None
    endereco = format_filial_address(filial)
    return {
        "id": str(filial.id),
        "codigo": filial.code,
        "nome": filial.name,
        "cidade": filial.city,
        "uf": filial.state,
        "cep": filial.zip_code,
        "logradouro": filial.address,
        "numero": filial.number,
        "complemento": filial.complement,
        "bairro": filial.district,
        "telefone": filial.phone,
        "endereco_formatado": endereco,
        "matriz": bool(filial.is_headquarters),
        "is_headquarters": bool(filial.is_headquarters),
        "latitude": lat,
        "longitude": lng,
    }
