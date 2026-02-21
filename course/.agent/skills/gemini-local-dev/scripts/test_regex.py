import re

content = """
import { GoogleGenAI } from "@google/genai";

export class GeminiService {
  private static async handleApiError(error: any): Promise<never> {
      console.log("error");
  }

  static async generateImage(prompt: string, config: { aspectRatio: AspectRatio; imageSize: ImageSize }): Promise<string> {
      console.log("generateImage");
  }

  async editImage(prompt: string, base64Image: string, maskBase64?: string): Promise<string> {
      console.log("editImage");
  }
}
"""

for match in re.finditer(r'(?:(?:public|private|protected|static)\s+)*(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\s*\{', content):
    print("Match:", match.group(1))
    func_signature = match.group(2)
    print("Sign:", func_signature)
    print("Start:", match.end())

