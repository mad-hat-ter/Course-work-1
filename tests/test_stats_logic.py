import pytest
from handlers.stats import _build_stats_message


@pytest.mark.asyncio
async def test_build_stats_message_single_sheet(monkeypatch, sample_settings, sample_sheet_entries):
    async def fake_settings():
        return sample_settings
    async def fake_refresh():
        return list(sample_sheet_entries.keys())
    async def fake_sheet_data(sheet):
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.stats.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.stats.refresh_schedule_sheets", fake_refresh)
    monkeypatch.setattr("handlers.stats.get_sheet_data", fake_sheet_data)
    text = await _build_stats_message("Аня Фролова", ["08.06–14.06"])
    assert text is not None
    assert "Пн 16:00" in text
    assert "Ср 12:00" in text
    assert text.index("Пн 16:00") < text.index("Ср 12:00")
    assert "800 ₽" in text


@pytest.mark.asyncio
async def test_build_stats_message_no_shifts(monkeypatch, sample_settings, sample_sheet_entries):
    async def fake_settings():
        return sample_settings
    async def fake_refresh():
        return list(sample_sheet_entries.keys())
    async def fake_sheet_data(sheet):
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.stats.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.stats.refresh_schedule_sheets", fake_refresh)
    monkeypatch.setattr("handlers.stats.get_sheet_data", fake_sheet_data)

    assert await _build_stats_message("Неизвестный", ["08.06–14.06"]) is None


@pytest.mark.asyncio
async def test_build_stats_message_unknown_sheet(monkeypatch, sample_settings):
    async def fake_settings():
        return sample_settings
    async def fake_refresh():
        return ["08.06–14.06"]
    monkeypatch.setattr("handlers.stats.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.stats.refresh_schedule_sheets", fake_refresh)
    assert await _build_stats_message("Аня Фролова", ["missing"]) is None


@pytest.mark.asyncio
async def test_build_stats_message_continues_on_sheet_error(
    monkeypatch, sample_settings, sample_sheet_entries
):
    async def fake_settings():
        return sample_settings
    async def fake_refresh():
        return ["broken", "08.06–14.06"]
    async def fake_sheet_data(sheet):
        if sheet == "broken":
            raise RuntimeError("network")
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.stats.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.stats.refresh_schedule_sheets", fake_refresh)
    monkeypatch.setattr("handlers.stats.get_sheet_data", fake_sheet_data)
    text = await _build_stats_message("Аня Фролова", ["broken", "08.06–14.06"])
    assert text is not None
    assert "08.06–14.06" in text
