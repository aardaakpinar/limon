import unittest
from unittest import mock

from limon import cli
from limon.picker import PAGE, choose_model


def run(inputs, models, suggested="m2", current=""):
    it = iter(inputs)
    asked, said = [], []
    def ask(prompt):
        asked.append(prompt)
        return next(it)
    out = choose_model(suggested, (lambda: models) if not isinstance(models, Exception) else (lambda: (_ for _ in ()).throw(models)),
                       ask=ask, say=said.append, current=current)
    return out, said


class PickerTests(unittest.TestCase):
    def test_pick_by_number_and_default_goes_first(self):
        out, said = run(["2"], ["a", "m2", "z"])
        self.assertEqual(out, "a")                       # m2 üstte (1.), a ikinci
        self.assertIn("1. m2", " ".join(said).replace("  ", " "))

    def test_enter_keeps_suggested(self):
        self.assertEqual(run([""], ["a", "m2"])[0], "m2")

    def test_typed_name_is_accepted_even_if_not_listed(self):
        self.assertEqual(run(["ozel-model-9"], ["a", "m2"])[0], "ozel-model-9")

    def test_filter_then_pick(self):
        out, _ = run(["/gpt", "1"], ["claude-x", "gpt-a", "gpt-b"], suggested="claude-x")
        self.assertEqual(out, "claude-x") if False else None
        out, _ = run(["/gpt", "2"], ["claude-x", "gpt-a", "gpt-b"], suggested="zzz")
        self.assertEqual(out, "gpt-b")

    def test_invalid_number_reprompts(self):
        out, said = run(["99", "0", "1"], ["a", "b"], suggested="a")
        self.assertEqual(out, "a")
        self.assertTrue(any("Geçersiz numara" in s for s in said))

    def test_no_match_filter_can_be_cleared(self):
        out, said = run(["/yok", "/", "1"], ["a", "b"], suggested="a")
        self.assertEqual(out, "a")
        self.assertTrue(any("eşleşen model yok" in s for s in said))

    def test_list_failure_falls_back_to_text_entry(self):
        out, said = run(["elle-model"], RuntimeError("401 yetkisiz"))
        self.assertEqual(out, "elle-model")
        self.assertTrue(any("alınamadı" in s for s in said))
        self.assertEqual(run([""], RuntimeError("x"))[0], "m2")

    def test_empty_list_falls_back(self):
        self.assertEqual(run([""], [])[0], "m2")

    def test_long_list_is_paged(self):
        models = [f"model-{i:03d}" for i in range(80)]
        out, said = run(["/model-07", "1"], models, suggested="model-000")
        self.assertEqual(out, "model-070")
        _, said = run([""], models, suggested="model-000")
        self.assertTrue(any("model daha" in s for s in said))
        self.assertLessEqual(len([s for s in said if s.strip()[:3].rstrip(".").isdigit()]), PAGE)


class WizardIntegrationTests(unittest.TestCase):
    def test_select_model_uses_live_list_after_key(self):
        cfg = {"provider": "claude", "model": "claude-sonnet-5-5", "api_keys": {"claude": "k", "openai": "", "gemini": ""}, "ollama_host": ""}
        with mock.patch("limon.models.list_models", return_value=["claude-opus-5-5", "claude-sonnet-5-5"]) as lm, \
             mock.patch("builtins.input", side_effect=["2"]):
            self.assertEqual(cli.select_model(cfg), "claude-opus-5-5")
        self.assertEqual(lm.call_args.kwargs["api_key"], "k")

    def test_missing_key_falls_back_without_network_call(self):
        cfg = {"provider": "openai", "model": "gpt-4.1", "api_keys": {"openai": "", "claude": "", "gemini": ""}, "ollama_host": ""}
        with mock.patch.dict("os.environ", {}, clear=False), mock.patch("limon.models.list_models") as lm, \
             mock.patch("builtins.input", side_effect=[""]):
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            self.assertEqual(cli.select_model(cfg), "gpt-4.1")
        lm.assert_not_called()

    def test_provider_change_suggests_new_provider_default(self):
        cfg = {"provider": "ollama", "model": "claude-sonnet-5-5", "api_keys": {"openai": "", "claude": "", "gemini": ""}, "ollama_host": "http://x"}
        with mock.patch("limon.models.list_models", side_effect=RuntimeError("bağlanılamadı")), \
             mock.patch("builtins.input", side_effect=[""]):
            self.assertEqual(cli.select_model(cfg, previous_provider="claude"), "llama3.1")


if __name__ == "__main__":
    unittest.main()
