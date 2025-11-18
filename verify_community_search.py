#!/usr/bin/env python3
"""Verification script to check CommunitySearch has correct attributes.

This script verifies that:
1. CommunitySearch has 'proxy' attribute (NOT 'ollama_client')
2. DualLevelSearch has 'proxy' attribute (NOT 'ollama_client')
3. All methods use proxy.generate() correctly
"""

import inspect


def verify_community_search():
    """Verify CommunitySearch implementation."""
    from src.components.graph_rag.community_search import CommunitySearch
    from src.components.graph_rag.dual_level_search import DualLevelSearch

    print("="  * 80)
    print("VERIFICATION: CommunitySearch AegisLLMProxy Migration")
    print("=" * 80)

    # Check class hierarchy
    print(f"\n1. Class Hierarchy:")
    print(f"   CommunitySearch inherits from: {CommunitySearch.__bases__}")
    print(f"   Expected: (<class 'src.components.graph_rag.dual_level_search.DualLevelSearch'>,)")

    # Check DualLevelSearch.__init__ source
    print(f"\n2. DualLevelSearch.__init__ Implementation:")
    init_source = inspect.getsource(DualLevelSearch.__init__)
    has_proxy = "self.proxy = get_aegis_llm_proxy()" in init_source
    has_ollama_client = "self.ollama_client" in init_source
    print(f"   - Has 'self.proxy = get_aegis_llm_proxy()': {has_proxy}")
    print(f"   - Has 'self.ollama_client': {has_ollama_client}")
    status_ok = "[OK]" if has_proxy and not has_ollama_client else "[FAIL]"
    print(f"   - Status: {status_ok}")

    # Check _generate_answer source
    print(f"\n3. DualLevelSearch._generate_answer Implementation:")
    gen_answer_source = inspect.getsource(DualLevelSearch._generate_answer)
    uses_proxy = "self.proxy.generate" in gen_answer_source
    uses_ollama = "self.ollama_client" in gen_answer_source
    print(f"   - Uses 'self.proxy.generate': {uses_proxy}")
    print(f"   - Uses 'self.ollama_client': {uses_ollama}")
    status_ok = "[OK]" if uses_proxy and not uses_ollama else "[FAIL]"
    print(f"   - Status: {status_ok}")

    # Check CommunitySearch methods
    print(f"\n4. CommunitySearch Implementation:")
    community_source = inspect.getsource(CommunitySearch)
    has_ollama_ref = "ollama_client" in community_source.replace("ollama_base_url", "")
    print(f"   - Contains 'ollama_client': {has_ollama_ref}")
    status_ok = "[OK]" if not has_ollama_ref else "[FAIL - needs migration]"
    print(f"   - Status: {status_ok}")

    # Check inherited methods
    print(f"\n5. Method Resolution Order:")
    print(f"   - CommunitySearch._generate_answer: {CommunitySearch._generate_answer}")
    print(f"   - DualLevelSearch._generate_answer: {DualLevelSearch._generate_answer}")
    inherits_correctly = (
        CommunitySearch._generate_answer == DualLevelSearch._generate_answer
    )
    print(f"   - Inherits _generate_answer: {inherits_correctly}")
    status_ok = "[OK]" if inherits_correctly else "[FAIL]"
    print(f"   - Status: {status_ok}")

    # Overall status
    print(f"\n" + "=" * 80)
    all_correct = has_proxy and not has_ollama_client and uses_proxy and not uses_ollama and not has_ollama_ref and inherits_correctly
    if all_correct:
        print("RESULT: [OK] ALL CHECKS PASSED - CommunitySearch is properly migrated")
    else:
        print("RESULT: [FAIL] MIGRATION INCOMPLETE - See details above")
    print("=" * 80)

    return all_correct


if __name__ == "__main__":
    verify_community_search()
