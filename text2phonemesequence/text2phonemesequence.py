import os
import re

from segments import Tokenizer
from tqdm import tqdm
from transformers import AutoTokenizer, T5ForConditionalGeneration
from unidecode import unidecode


class Text2PhonemeSequence:
    def __init__(
        self,
        pretrained_g2p_model="charsiu/g2p_multilingual_byT5_small_100",
        tokenizer="google/byt5-small",
        language="vie-n",
        g2p_dict_path=None,
        device="cuda:0",
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer)
        self.model = T5ForConditionalGeneration.from_pretrained(pretrained_g2p_model)
        self.device = device
        if "cuda" in self.device:
            self.model = self.model.to(self.device)
        self.punctuation = (
            list('.?!,:;-()[]{}<>"') + list("'/‘”“/&#~@^|") + ["...", "*"]
        )
        self.segment_tool = Tokenizer()
        self.phoneme_length = {
            "msa.tsv": 27,
            "amh.tsv": 28,
            "urd.tsv": 152,
            "mri.tsv": 30,
            "glg.tsv": 22,
            "swa.tsv": 28,
            "est.tsv": 47,
            "hbs-latn.tsv": 31,
            "spa.tsv": 28,
            "pol.tsv": 38,
            "spa-latin.tsv": 24,
            "fra.tsv": 43,
            "uig.tsv": 33,
            "aze.tsv": 34,
            "nob.tsv": 52,
            "swe.tsv": 36,
            "por-bz.tsv": 28,
            "arg.tsv": 30,
            "yue.tsv": 227,
            "sqi.tsv": 42,
            "cat.tsv": 27,
            "hbs-cyrl.tsv": 31,
            "grc.tsv": 39,
            "bak.tsv": 44,
            "hun.tsv": 67,
            "lat-clas.tsv": 61,
            "ita.tsv": 37,
            "san.tsv": 38,
            "arm-w.tsv": 41,
            "afr.tsv": 81,
            "ind.tsv": 87,
            "sme.tsv": 31,
            "egy.tsv": 22,
            "rus.tsv": 62,
            "ady.tsv": 29,
            "epo.tsv": 43,
            "srp.tsv": 42,
            "zho-t.tsv": 135,
            "tha.tsv": 295,
            "vie-c.tsv": 184,
            "kur.tsv": 37,
            "ice.tsv": 37,
            "geo.tsv": 75,
            "cze.tsv": 43,
            "ara.tsv": 370,
            "tgl.tsv": 27,
            "nan.tsv": 175,
            "por-po.tsv": 35,
            "bos.tsv": 52,
            "enm.tsv": 24,
            "ltz.tsv": 55,
            "ina.tsv": 26,
            "ukr.tsv": 39,
            "mac.tsv": 44,
            "kaz.tsv": 44,
            "slk.tsv": 73,
            "ang.tsv": 33,
            "khm.tsv": 47,
            "syc.tsv": 24,
            "eus.tsv": 35,
            "spa-me.tsv": 28,
            "tts.tsv": 26,
            "gle.tsv": 36,
            "slv.tsv": 35,
            "ido.tsv": 23,
            "zho-s.tsv": 135,
            "vie-n.tsv": 174,
            "gre.tsv": 20,
            "eng-us.tsv": 119,
            "fin.tsv": 44,
            "pap.tsv": 26,
            "tuk.tsv": 49,
            "jpn.tsv": 174,
            "bel.tsv": 58,
            "uzb.tsv": 36,
            "dan.tsv": 42,
            "ori.tsv": 45,
            "ron.tsv": 30,
            "bul.tsv": 40,
            "bur.tsv": 52,
            "lit.tsv": 87,
            "dut.tsv": 48,
            "fra-qu.tsv": 255,
            "eng-uk.tsv": 129,
            "hin.tsv": 110,
            "isl.tsv": 41,
            "arm-e.tsv": 38,
            "kor.tsv": 175,
            "tur.tsv": 54,
            "fas.tsv": 70,
            "ger.tsv": 56,
            "tam.tsv": 38,
            "wel-sw.tsv": 44,
            "vie-s.tsv": 172,
            "mlt.tsv": 47,
            "wel-nw.tsv": 49,
            "slo.tsv": 27,
            "lat-eccl.tsv": 43,
            "snd.tsv": 60,
            "tat.tsv": 103,
            "alb.tsv": 40,
            "hau.tsv": 45,
            "pus.tsv": 34,
            "tib.tsv": 61,
            "sga.tsv": 47,
            "heb.tsv": 39,
            "hrx.tsv": 27,
            "fao.tsv": 42,
            "dsb.tsv": 29,
        }

        self.phone_dict = {}

        if g2p_dict_path is None or os.path.exists(g2p_dict_path) is False:
            if os.path.exists("./" + language + ".tsv"):
                g2p_dict_path = "./" + language + ".tsv"
            else:
                os.system(
                    "wget https://raw.githubusercontent.com/lingjzhu/CharsiuG2P/main/dicts/"
                    + language
                    + ".tsv"
                )
                g2p_dict_path = "./" + language + ".tsv"
        else:
            if language is None or len(language) == 0:
                language = g2p_dict_path.split("/")[-1].split(".")[0]

        if f"{language}.tsv" not in self.phoneme_length:
            raise ValueError(
                f"Language {language} not supported. Please check the phoneme length dictionary."
            )

        self.language = language

        if os.path.exists(g2p_dict_path):
            f = open(g2p_dict_path, "r", encoding="utf-8")
            list_words = f.read().strip().split("\n")
            f.close()
            for word_phone in list_words:
                w_p = word_phone.split("\t")
                assert len(w_p) == 2, print(w_p)
                if "," not in w_p[1]:
                    self.phone_dict[w_p[0]] = [w_p[1]]
                else:
                    self.phone_dict[w_p[0]] = [w_p[1].split(",")[0]]

    def infer_dataset(
        self,
        input_file="",
        seperate_syllabel_token="_",
        output_file="",
        batch_size = 1,
    ):
        print("Building vocabulary!")

        # Write results to output file
        with open(input_file, "r") as f:
            list_lines = f.readlines()

        with open(output_file, "w") as f:
            for line in tqdm(list_lines):
                line = line.strip().split("|")
                prefix = line[0]
                text = line[-1]

                phonemes = self.infer_sentence(text, seperate_syllabel_token)

                if len(line) == 3:  # for multi speakers
                    f.write(prefix + "|" + line[1] + "|" + phonemes)
                else:
                    f.write(prefix + "|" + phonemes)
                f.write("\n")

    def t2p(self, text: str, using_model: bool = True) -> str:
        if text in self.phone_dict and using_model is False:
            return self.phone_dict[text][0]
        elif text in self.punctuation:
            return text
        else:
            if all([t in self.phone_dict for t in text.split(" ")]) and using_model is False:
                phones = ""
                for t in text.split(" "):
                    if t in self.phone_dict:
                        phones += self.phone_dict[t][0]
                return phones
            else:
                out = self.tokenizer(
                    "<" + self.language + ">: " + text,
                    padding=True,
                    add_special_tokens=False,
                    return_tensors="pt",
                )
                if "cuda" in self.device:
                    out["input_ids"] = out["input_ids"].to(self.device)
                    out["attention_mask"] = out["attention_mask"].to(self.device)
                if self.language + ".tsv" not in self.phoneme_length.keys():
                    self.phoneme_length[self.language + ".tsv"] = 50
                preds = self.model.generate(
                    **out,
                    num_beams=1,
                    max_length=self.phoneme_length[self.language + ".tsv"],
                )
                phones = self.tokenizer.batch_decode(
                    preds.tolist(), skip_special_tokens=True
                )
                return phones[0]

    def infer_sentence(self, sentence="", seperate_syllabel_token="_"):
        list_words = sentence.split(" ")
        list_phones = []
        for i in range(len(list_words)):
            list_words[i] = list_words[i].replace(seperate_syllabel_token, " ")
            phoneme = self.t2p(list_words[i])
            list_phones.append(phoneme)

            list_phones[-1] = self.postprocess_phonemes(list_words[i], list_phones[-1])

        for i in range(len(list_phones)):
            try:
                segmented_phone = self.segment_tool(list_phones[i], ipa=True)
            except:
                segmented_phone = self.segment_tool(list_phones[i])
            list_phones[i] = segmented_phone
        return " ▁ ".join(list_phones)

    def postprocess_phonemes(self, text: str, phonemes: str) -> str:
        phoneme_replacements = {
            r"^(?=.*uy)(?!.*ui).*$": {
                "uj": "wi",
            },
            r"^gi|\sgi($|\s)": {
                "ɣi": "zi",
            },
            r"oo": {"ɔ": "ɔɔ"},
            r"^r": {
                "z": "r",
            },
        }

        if "vie" in self.language:
            for pattern, replacements in phoneme_replacements.items():
                for t in text.split():
                    match = re.search(pattern, unidecode(t).lower())
                    if match:
                        for key, value in replacements.items():
                            phonemes = phonemes.replace(key, value)

        return phonemes


if __name__ == "__main__":

    model = Text2PhonemeSequence(
        g2p_dict_path="vie-n.unique.tsv",
        device="cpu",
        language = "vie-n",
    )
    # model.infer_dataset(
    #     input_file="input.txt",
    #     output_file="new_output.txt",
    # )
    model.infer_sentence("roong")
