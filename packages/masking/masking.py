import re
import time
import hashlib
from typing import Dict, Tuple, Optional
from packages.synthetic_dictionary.dictionary import SyntheticDictionary
from packages.rule_cache.cache import rule_cache

# ─── TTL-based mapping store ───────────────────────────────────

class _TTLMappingStore:
    """
    Stockage de mappings inversés avec TTL et purge automatique.
    Les mappings expirent après `ttl_seconds` et sont purgés après usage.
    """
    def __init__(self, ttl_seconds: int = 3600):
        self._store: Dict[str, Tuple[str, float]] = {}  # key -> (value, expires_at)
        self._ttl = ttl_seconds

    def set(self, key: str, value: str):
        self._store[key] = (value, time.time() + self._ttl)

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def get_all_valid(self) -> Dict[str, str]:
        """Retourne tous les mappings non expirés."""
        now = time.time()
        result = {}
        expired_keys = []
        for key, (value, expires_at) in self._store.items():
            if now > expires_at:
                expired_keys.append(key)
            else:
                result[key] = value
        # Purge expired
        for k in expired_keys:
            del self._store[k]
        return result

    def purge_used(self, keys: list):
        """Purge les mappings après utilisation pour le démasquage."""
        for k in keys:
            self._store.pop(k, None)

    def purge_all(self):
        self._store.clear()

    def __len__(self):
        return len(self._store)


class MaskingService:
    def __init__(self):
        # Mappings inversés avec TTL de 1h et purge après démasquage
        self._reverse_store = _TTLMappingStore(ttl_seconds=3600)

    def _get_entity_type(self, entity: str) -> str:
        """Détermine le type d'entité (prénom, nom de famille ou ville) à des fins de remplacement."""
        # Simple heuristique basée sur les listes de base de SyntheticDictionary
        from packages.synthetic_dictionary.dictionary import BASE_PRENOMS, BASE_NOMS, BASE_LIEUX
        entity_lower = entity.lower()
        if any(p.lower() == entity_lower for p in BASE_PRENOMS):
            return "names"
        if any(l.lower() == entity_lower for l in BASE_LIEUX):
            return "cities"
        return "surnames"

    def _approximate_number(self, match_str: str) -> str:
        """Arrondit un nombre ou un montant de manière réaliste (ex: 1200 € -> ~1000 €)."""
        num_match = re.search(r'\d+', match_str)
        if not num_match:
            return match_str
        num_val = int(num_match.group(0))
        if num_val < 5:
            approx = "~1"
        elif num_val < 10:
            approx = "~5"
        else:
            order = 10 ** (len(str(num_val)) - 1)
            approx = f"~{round(num_val / order) * order}"
        return match_str.replace(num_match.group(0), approx)

    def _safe_regex_finditer(self, pattern: str, text: str, max_matches: int = 50, timeout_hint_ms: int = 100):
        """
        Wrapper sécurisé autour de re.finditer.
        Limite le nombre de matches et détecte les regex trop lentes.
        """
        matches = []
        start_time = time.monotonic()
        try:
            for i, m in enumerate(re.finditer(pattern, text)):
                if i >= max_matches:
                    break
                elapsed_ms = (time.monotonic() - start_time) * 1000
                if elapsed_ms > timeout_hint_ms:
                    print(f"[Masking] ⚠️ Regex timeout ({elapsed_ms:.0f}ms) pour pattern: {pattern[:50]}")
                    break
                matches.append(m)
        except re.error as e:
            print(f"[Masking] Regex error: {e} pour pattern: {pattern[:50]}")
        return matches

    def mask_message(
        self,
        text: str,
        org_id: str,
        seed: str,
        active_rules: Dict[str, bool],
        rule_levels: Dict[str, str],
        custom_rules: list
    ) -> Tuple[str, Dict[str, str]]:
        """
        Brouille les données du message en appliquant la stratégie adéquate selon le niveau.
        Retourne le texte brouillé et la table de correspondance (mapping).
        """
        masked_text = text
        mapping: Dict[str, str] = {}
        
        # Génération du dictionnaire synthétique privé pour cette organisation
        dict_data = SyntheticDictionary.generate_dictionary(seed)
        
        # 1. Gestion du type d'action par catégorie de règle
        # Niveaux possibles : delete (suppression), high (brouillage synthétique), medium/low (alias token/approx)
        
        # --- CONTACTS (Emails & Téléphones) ---
        if active_rules.get("contact", True):
            level = rule_levels.get("contact", "medium")
            # Emails
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            for match in re.finditer(email_pattern, text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[EMAIL_SUPPRIMÉ]"
                elif level == "high":
                    # Remplacement synthétique déterministe
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = rule_cache.get_mapping(org_id, entity_hash)
                    if not replacement:
                        # Génère un email synthétique à partir du dictionnaire
                        index = int(entity_hash, 16)
                        name = dict_data["names"][index % len(dict_data["names"])].lower()
                        surname = dict_data["surnames"][index % len(dict_data["surnames"])].lower()
                        replacement = f"{name}.{surname}@kinga-synthetic.com"
                        rule_cache.set_mapping(org_id, entity_hash, replacement)
                else:
                    # Alias standard
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[EMAIL_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

            # Téléphones
            phone_pattern = r'\+?\d{1,3}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            for match in re.finditer(phone_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[TEL_SUPPRIMÉ]"
                elif level == "high":
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = rule_cache.get_mapping(org_id, entity_hash)
                    if not replacement:
                        index = int(entity_hash, 16)
                        replacement = f"+33 6 {index % 90 + 10} {index % 89 + 10} {index % 88 + 10} {index % 87 + 10}"
                        rule_cache.set_mapping(org_id, entity_hash, replacement)
                else:
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[TEL_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

        # --- FINANCE (Montants) ---
        if active_rules.get("finance", True):
            level = rule_levels.get("finance", "low")
            money_pattern = r'\b\d+(?:[.,]\d+)?\s*(?:€|\$|FCFA|XOF|XAF)\b'
            for match in re.finditer(money_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[MONTANT_SUPPRIMÉ]"
                elif level == "low":
                    # Approximation réaliste (ex: 1200 € -> ~1000 €)
                    replacement = self._approximate_number(original)
                elif level == "medium":
                    # Token anonyme
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[MONTANT_{int(entity_hash[:4], 16) % 100 + 1}]"
                else:
                    # High — montant synthétique déterministe
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = rule_cache.get_mapping(org_id, entity_hash)
                    if not replacement:
                        index = int(entity_hash, 16)
                        # Générer un montant réaliste dans le même ordre de grandeur
                        num_match = re.search(r'\d+', original)
                        if num_match:
                            orig_val = int(num_match.group(0))
                            order = 10 ** max(0, len(str(orig_val)) - 1)
                            synth_val = (index % 9 + 1) * order
                            currency_match = re.search(r'(€|\$|FCFA|XOF|XAF)', original)
                            currency = currency_match.group(0) if currency_match else "€"
                            replacement = f"{synth_val} {currency}"
                        else:
                            replacement = f"[MONTANT_{int(entity_hash[:4], 16) % 100 + 1}]"
                        rule_cache.set_mapping(org_id, entity_hash, replacement)
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

        # --- NAMES (Noms propres / Villes) ---
        if active_rules.get("names", True):
            level = rule_levels.get("names", "high")
            # Liste simple de noms de test pour la démo NER light
            names_pattern = r'\b(?:Jean|Dupont|Alice|Bob|Charlie|Martin|Thomas|Moussa|Diop|Koné|Paris|Lyon|Dakar|Abidjan)\b'
            for match in re.finditer(names_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[NOM_SUPPRIMÉ]"
                elif level == "high":
                    # Dictionnaire synthétique déterministe
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = rule_cache.get_mapping(org_id, entity_hash)
                    if not replacement:
                        entity_type = self._get_entity_type(original)
                        options = dict_data[entity_type]
                        index = int(entity_hash, 16) % len(options)
                        replacement = options[index]
                        rule_cache.set_mapping(org_id, entity_hash, replacement)
                else:
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[NOM_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

        # --- DATES ---
        if active_rules.get("dates", True):
            level = rule_levels.get("dates", "medium")
            date_pattern = r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b'
            for match in re.finditer(date_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[DATE_SUPPRIMÉE]"
                elif level == "high":
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = rule_cache.get_mapping(org_id, entity_hash)
                    if not replacement:
                        index = int(entity_hash, 16)
                        replacement = f"{index % 28 + 1:02d}/{index % 12 + 1:02d}/2026"
                        rule_cache.set_mapping(org_id, entity_hash, replacement)
                else:
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[DATE_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

        # --- DOCUMENTS ---
        if active_rules.get("documents", True):
            level = rule_levels.get("documents", "medium")
            # Cartes bancaires
            card_pattern = r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'
            for match in re.finditer(card_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[CARTE_SUPPRIMÉE]"
                else:
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[CARTE_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

            # Numéros de sécurité sociale (SSN)
            ssn_pattern = r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b'
            for match in re.finditer(ssn_pattern, masked_text):
                original = match.group(0)
                if level == "delete":
                    replacement = "[SSN_SUPPRIMÉ]"
                else:
                    entity_hash = hashlib.sha256(f"{original}{seed}".encode('utf-8')).hexdigest()
                    replacement = f"[SSN_{int(entity_hash[:4], 16) % 100 + 1}]"
                
                masked_text = masked_text.replace(original, replacement)
                mapping[original] = replacement

        # --- RÈGLES PERSONNALISÉES (CUSTOM REGEX) ---
        for cr in custom_rules:
            is_active = cr.get("isActive") if isinstance(cr, dict) else cr.isActive
            pattern = cr.get("pattern") if isinstance(cr, dict) else cr.pattern
            alias_format = cr.get("format") if isinstance(cr, dict) else cr.format
            if not is_active or not pattern:
                continue
            # Use safe regex execution with timeout and match limit
            matches = self._safe_regex_finditer(pattern, masked_text, max_matches=50, timeout_hint_ms=100)
            counter = 1
            for match in matches:
                original = match.group(0)
                fmt = alias_format or f"[CUSTOM_{counter}]"
                replacement = fmt.replace("{n}", str(counter))
                masked_text = masked_text.replace(original, replacement, 1)
                mapping[original] = replacement
                counter += 1

        # Mise en cache avec TTL pour le démasquage dans cette session
        for orig, repl in mapping.items():
            self._reverse_store.set(repl, orig)
            
        return masked_text, mapping

    def unmask_message(self, masked_text: str) -> str:
        """Restaure le texte original à partir du texte brouillé. Purge les mappings après usage."""
        unmasked_text = masked_text
        valid_mappings = self._reverse_store.get_all_valid()
        used_keys = []
        for token, original in valid_mappings.items():
            if token in unmasked_text:
                unmasked_text = unmasked_text.replace(token, original)
                used_keys.append(token)
        # Purge les mappings utilisés pour limiter l'exposition en mémoire
        self._reverse_store.purge_used(used_keys)
        return unmasked_text
