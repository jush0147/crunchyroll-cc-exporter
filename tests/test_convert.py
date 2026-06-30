from crunchyroll_cc_exporter.convert import vtt_to_srt


def test_vtt_to_srt_strips_tags_and_converts_timestamps():
    vtt = """WEBVTT

00:00:03.295 --> 00:00:06.882 line:90% align:center
<Default><b>[DIPLOMAT A] I need to be
at the embassy ASAP.</b></Default>

00:00:06.924 --> 00:00:09.969 line:90% align:center
<Default><i>Hello</i> &amp; goodbye.</Default>
"""
    srt = vtt_to_srt(vtt)
    assert "00:00:03,295 --> 00:00:06,882" in srt
    assert "[DIPLOMAT A] I need to be\nat the embassy ASAP." in srt
    assert "<Default>" not in srt
    assert "Hello & goodbye." in srt


def test_vtt_to_srt_skips_note_blocks():
    vtt = """WEBVTT

NOTE
This should be ignored.

00:00:01.000 --> 00:00:02.000
Visible text.
"""
    srt = vtt_to_srt(vtt)
    assert "This should be ignored" not in srt
    assert "Visible text." in srt
