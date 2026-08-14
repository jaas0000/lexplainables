import type { components } from "@/generated/types";

export type Categorie = components["schemas"]["FeedbackRead"]["categorie"];

export const CATEGORIE_META: Record<Categorie, { label: string; kleurVar: string }> = {
  verbeteridee:    { label: "Verbeteridee",    kleurVar: "--info" },
  probleemmelding: { label: "Probleemmelding", kleurVar: "--fout" },
  compliment:      { label: "Compliment",      kleurVar: "--succes" },
  vraag:           { label: "Vraag",           kleurVar: "--waarschuwing" },
};

export const CATEGORIEN: Categorie[] = ["verbeteridee", "probleemmelding", "compliment", "vraag"];
