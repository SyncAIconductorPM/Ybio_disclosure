"""
tests/test_data_source.py – DataSource Protocol 및 YamlDataSource 단위 테스트
"""

from pathlib import Path
import pytest

from api.services.data_source import DataSourceProtocol, YamlDataSource


def test_yaml_data_source_implements_protocol():
    """YamlDataSource가 DataSourceProtocol 인터페이스를 구현하는지 검증"""
    source = YamlDataSource()
    assert isinstance(source, DataSourceProtocol)


def test_yaml_data_source_list_and_load():
    """samples/ YAML 파일 목록 조회 및 플레이스홀더 치환 검증"""
    source = YamlDataSource()
    forms = source.list_forms()
    assert isinstance(forms, list)

    if forms:
        data = source.load_form_data(forms[0])
        assert isinstance(data, dict)
        assert "event" in data or "title" in data
