import json
import subprocess
import logging

# Use codex exec to read the reviews' json file, and generate a review summary and make recommendations
class ReviewAnalyzer:
    def __init__(self, asin: str) -> None:
        self.asin = asin
        self.reviews = []
        self.summary = ""
        self.recommendation = ""

    def load_reviews(self):
        with open(self.asin + "-reviews.json", "r") as f:
            reviews = json.load(f)
        # Put the reviews title, rating, and body to one string to help chatgpt, and put it in a list
        self.product_name = reviews[0]["product_name"]
        self.reviews = [
            "Review Title: "
            + review["title"]
            + " Review Rating: "
            + str(review["star_rating"])
            + " Review Body: "
            + review["body"]
            for review in reviews[1:]  # the first one is the product name
        ]

    def call_codex(self, prompt):
        """Llama a codex exec de forma segura"""
        try:
            logging.info(f"Calling Codex with prompt length: {len(prompt)}")

            import os

            # Ejecutar como usuario hector con ruta completa a codex
            codex_cmd = '/home/hector/.nvm/versions/node/v20.19.4/bin/codex'

            result = subprocess.run(
                ['sudo', '-u', 'hector', codex_cmd, 'exec', prompt],
                capture_output=True,
                text=True,
                timeout=60,
                cwd='/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer'
            )

            if result.returncode != 0:
                error_msg = f"Codex error: {result.stderr}"
                logging.error(error_msg)
                return "Error al analizar reseñas. Por favor intenta de nuevo."

            # Extraer solo la respuesta (última línea del output)
            # Codex imprime headers y metadata, la respuesta real está al final
            output_lines = result.stdout.strip().split('\n')
            response = output_lines[-1] if output_lines else ""

            logging.info(f"Codex response received: {len(response)} chars")
            return response

        except subprocess.TimeoutExpired:
            logging.error("Codex timeout after 60s")
            return "El análisis tomó demasiado tiempo. Intenta con menos reseñas."
        except FileNotFoundError:
            logging.error("Codex CLI not found. Make sure 'codex' is installed and in PATH")
            return "Error: Codex CLI no está instalado. Instala con: pip install codex-cli"
        except Exception as e:
            logging.error(f"Exception calling Codex: {e}")
            return f"Error técnico: {str(e)}"

    def generate_summary(self):
        prompt = (
            "Can you summarize the reviews for "
            + self.product_name
            + " ? Here are the reviews:"
            + "\n\n".join(self.reviews)
            + "\n\nResponde en español."
        )
        return self.call_codex(prompt)

    def generate_pro_cons(self):
        prompt = (
            "Based on the reviews for "
            + self.product_name
            + ", can you 1. list three pros and 2. list three cons mentioned by customers? Here are the reviews: "
            + "\n\n".join(self.reviews)
            + "\n\nResponde en español."
        )
        return self.call_codex(prompt)

    def generate_recommendation(self):
        prompt = (
            "Based on the reviews of "
            + self.product_name
            + ", would you recommend to buy it? Here are the reviews: "
            + "\n\n".join(self.reviews)
            + "\n\nResponde en español."
        )
        return self.call_codex(prompt)

    def generate_buy_together(self):
        prompt = (
            "Can you recommend a product that I should buy together with "
            + self.product_name
            + "?"
            + "\n\n".join(self.reviews)
            + "\n\nResponde en español."
        )
        return self.call_codex(prompt)
