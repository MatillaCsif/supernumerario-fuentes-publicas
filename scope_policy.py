"""Project the retained archive onto the user's General Administration scope.

Official issuer metadata and explicit personnel labels determine exclusions.
Sanidad/Educación alone never determine a personnel regime or exclusion.
The retained acquisition archive is never deleted by this projection.
"""
import re
import unicodedata
import json
from pathlib import Path
from collections import Counter, defaultdict

SCOPE = 'ADMINISTRACION_GENERAL_JCYL'


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold())
                   if not unicodedata.combining(c))


def exclusion_reason(title, organism='', official_gazette=False):
    text = fold(title)
    issuer = fold(organism)
    # These bodies remain outside the user's scope even when a notice is
    # published by a ministry. Election permissions are not Cortes recruitment.
    if re.search(r'consejo (?:de cuentas|consultivo|economico y social)|'
                 r'procurador del comun|instituto (?:para la )?competitividad empresarial|'
                 r'instituto tecnologico agrario|ente publico regional de la energia|fundacion siglo|'
                 r'\bicecyl\b|agencia para la calidad del sistema universitario', text):
        return 'OTHER_ENTITY'
    if 'cortes de castilla y leon' in issuer or re.search(
            r'(?:personal|plazas|puestos|cuerpo|escala).{0,140}(?:de las|en las) cortes de castilla y leon', text):
        return 'CORTES'
    if re.search(r'funcionarios? docentes?|personal docente|cuerpos? de maestros|'
                 r'cuerpos?.{0,45}(?:profesores|catedraticos)|profesorado|'
                 r'profesores? de (?:ensenanza|educacion secundaria|religion)|'
                 r'inspectores de educacion|inspeccion educativa', text):
        return 'TEACHING'
    # Common competitions can admit statutory staff to AG posts. That explicit
    # AG destination is retained; SACYL category recruitment is excluded.
    ag_destination = bool(re.search(r'administracion general de (?:la comunidad|castilla y leon)', text))
    if not ag_destination and re.search(r'\bsacyl\b|servicio de salud de castilla y leon|'
                                       r'gerencia regional de salud|personal estatutario', text + ' ' + issuer):
        return 'SACYL_STATUTORY'
    if re.search(r'ayuntamiento|diputacion|mancomunidad|administracion local|'
                 r'policia local|'
                 r'habilitacion (?:de caracter )?nacional', issuer + ' ' + text):
        return 'LOCAL_ADMINISTRATION'
    if issuer.startswith(('universidad', 'universidades')):
        return 'UNIVERSITY'
    if official_gazette:
        # The source index contains universities and independent institutions.
        # Only the AG issuers represented by this corpus are admitted.
        if not (issuer.startswith('consejeria ') or
                issuer.startswith('gerencia de servicios sociales') or
                issuer.startswith('servicio publico de empleo de castilla y leon')):
            return 'OTHER_ISSUER' if issuer else 'UNCLASSIFIED_ISSUER'
    return None


def public_health_civil(title):
    text = fold(title)
    return bool(re.search(r'\b(?:jefe de seccion de epidemiologia|medico de salud publica)\b', text)
                and 'servicio territorial de sanidad' in text)


def project_scope(records, documents, links,excluded_position_codes=()):
    """Return an internally closed graph; archive-only records have no RPT edges."""
    excluded = {}
    for key, record in records.items():
        reason = exclusion_reason(record.get('title', ''),
                                  record.get('bocyl_metadata', {}).get('Organismo', ''),
                                  record.get('kind') == 'BOCYL_PUBLICATION')
        if reason:
            excluded[key] = reason
    # An otherwise generic phase follows its explicit owning dossier.
    while True:
        inherited = {key: 'EXCLUDED_PARENT' for key, r in records.items()
                     if key not in excluded and r.get('kind') == 'PHASE'
                     and r.get('parent_call_ids')
                     and all(parent in excluded for parent in r['parent_call_ids'])}
        if not inherited:
            break
        excluded.update(inherited)
    kept = {k: r for k, r in records.items() if k not in excluded}
    referenced = {did for r in kept.values() for did in r.get('documents', [])}
    referenced.update(did for r in kept.values() for did in r.get('archived_incomplete_document_ids', []))
    referenced.update(did for did, d in documents.items()
                      if d.get('association_status') == 'GENERAL_INFORMATION')
    kept_documents = {did: d for did, d in documents.items() if did in referenced}
    # This inverse belongs to the funcionario RPT directory. A laboral code
    # with the same digits denotes a different position namespace.
    laboral_links={lid:l for lid,l in links.items() if l['call_id'] in kept
                   and kept[l['call_id']].get('regime')=='Personal laboral'}
    for link in laboral_links.values():
        record=kept[link['call_id']]
        record.setdefault('separate_position_references',[]).append({
            **link,'namespace':'LABORAL_AG','funcionario_rpt_link':False,
            'verification':'Referencia a puesto laboral; no se identifica con un código de RPT funcionario por coincidencia numérica'})
    excluded_position_codes=set(excluded_position_codes)
    outside_postings={lid:l for lid,l in links.items() if l['call_id'] in kept
                      and lid not in laboral_links and l['rpt'] in excluded_position_codes}
    for link in outside_postings.values():
        kept[link['call_id']].setdefault('separate_position_references',[]).append({
            **link,'namespace':'EXCLUDED_ORGANIZATION_POSTING','active_rpt_link':False,
            'verification':'Código conservado en la evidencia; puesto adscrito a un organismo excluido expresamente del Atlas'})
    kept_links = {lid: l for lid, l in links.items() if l['call_id'] in kept
                  and lid not in laboral_links and lid not in outside_postings
                  and (not l.get('document_id') or l['document_id'] in kept_documents)}
    by_rpt = defaultdict(list)
    for lid, link in kept_links.items():
        by_rpt[link['rpt']].append(lid)
    for r in kept.values():
        r['documents'] = [did for did in r.get('documents', []) if did in kept_documents]
        r['position_links'] = [lid for lid in r.get('position_links', []) if lid in kept_links]
        r['parent_call_ids'] = [pid for pid in r.get('parent_call_ids', []) if pid in kept]
        r['phases'] = [p for p in r.get('phases', []) if p.get('asset_key') not in excluded]
        r['administrative_scope'] = SCOPE
    report = {'id': SCOPE, 'personnel': ['Personal funcionario', 'Personal laboral'],
              'excluded_record_ids': excluded,
              'excluded_document_sha256': sorted({d['sha256'] for did,d in documents.items() if did not in kept_documents and d.get('sha256')}),
              'excluded_records': len(excluded), 'excluded_by_reason': dict(Counter(excluded.values())),
              'excluded_documents': len(documents) - len(kept_documents),
              'excluded_rpt_links': len(links) - len(kept_links) - len(laboral_links)-len(outside_postings),
              'laboral_references_separated_from_funcionario_rpt':len(laboral_links),
              'excluded_organization_position_references':len(outside_postings),
              'archive_preserved': True, 'outside_scope_is_not_a_coverage_gap': True}
    return kept, kept_documents, kept_links, dict(by_rpt), report


def excluded_gazette_ids(root):
    path = Path(root) / '00_CONTROL/INTEGRACION_CONVOCATORIAS_20261016/BOCYL_HISTORICAL_AUDIT.json'
    if not path.is_file():
        return set()
    source = json.loads(path.read_text(encoding='utf-8'))
    return {r['id'] for r in source['records']
            if exclusion_reason(r['title'], r.get('metadata', {}).get('Organismo', ''), True)}
