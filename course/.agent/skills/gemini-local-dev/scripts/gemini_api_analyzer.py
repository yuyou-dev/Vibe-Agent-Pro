#!/usr/bin/env python3
"""
Gemini API 分析器 - Vibe Agent 风格

功能:
1. 扫描源代码找出使用的API调用
2. 从 gemini_models_config.json 加载模型配置
3. 根据代码特征匹配对应的模型
4. 生成REST调用示例代码和返回结果

使用方式:
    python gemini_api_analyzer.py
    或
    from gemini_api_analyzer import analyze
    analyzer = analyze()
    analyzer.print_report()
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class APICall:
    """API调用信息"""
    function: str
    file: str
    line: int
    has_image: bool = False
    has_audio: bool = False
    has_video: bool = False
    has_stream: bool = False
    has_tts: bool = False
    has_structured: bool = False
    detected_model: str = ""
    matched_config: Optional[Dict[str, Any]] = None
    extracted_params: Dict[str, Any] = field(default_factory=dict)
    image_params: List[str] = field(default_factory=list)  # 图片参数名称列表


@dataclass
class ModelConfig:
    """模型配置（从JSON加载）"""
    model: str
    name: str
    category: str
    description: str
    api_version: str
    endpoint: str
    request_template: Dict[str, Any]
    response_example: Any
    extract_path: str
    use_cases: List[str]
    keywords: List[str]
    default_params: Dict[str, Any] = field(default_factory=dict)


class GeminiAnalyzer:
    """Gemini API 分析器"""

    def __init__(self, project_root: Path, config_path: Optional[Path] = None):
        self.root = project_root
        self.api_calls: List[APICall] = []
        self.model_configs: Dict[str, ModelConfig] = {}

        # 默认配置文件路径
        if config_path:
            self.config_path = config_path
        else:
            # 尝试从多个位置加载
            possible_paths = [
                # 1. 相对路径: ../resources/ (标准 Skill 结构)
                Path(__file__).parent.parent / "resources" / "gemini_models_config.json",
                # 2. 同级目录 (旧兼容)
                Path(__file__).parent / "gemini_models_config.json",
            ]
            found_path = None
            for p in possible_paths:
                if p.exists():
                    found_path = p
                    break
            self.config_path = found_path

        self._load_config()

    def _load_config(self):
        """从JSON加载模型配置"""
        if not self.config_path:
            print("⚠️  未找到模型配置文件。请确保 'gemini_models_config.json' 存在于预期位置。")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            for model_id, model_data in config_data.get('models', {}).items():
                self.model_configs[model_id] = ModelConfig(
                    model=model_id,
                    name=model_data.get('name', ''),
                    category=model_data.get('category', ''),
                    description=model_data.get('description', ''),
                    api_version=model_data.get('api_version', 'v1beta'),
                    endpoint=model_data.get('endpoint', 'generateContent'),
                    request_template=model_data.get('request_template', {}),
                    response_example=model_data.get('response_example', {}),
                    extract_path=model_data.get('extract_path', ''),
                    use_cases=model_data.get('use_cases', []),
                    keywords=model_data.get('keywords', []),
                    default_params=model_data.get('default_params', {})
                )

            print(f"✅ 加载了 {len(self.model_configs)} 个模型配置")
        except FileNotFoundError:
            print(f"⚠️  配置文件未找到: {self.config_path}")
        except json.JSONDecodeError as e:
            print(f"⚠️  配置文件解析错误: {e}")

    def scan(self) -> List[APICall]:
        """扫描源代码找出API调用"""
        calls = []

        # 扫描 TypeScript/JavaScript 文件
        for ts_file in self.root.rglob('*.ts*'):
            if any(x in str(ts_file) for x in ['node_modules', '.agent', 'dist', 'build']):
                continue
            try:
                content = ts_file.read_text(encoding='utf-8')
                file_calls = self._parse_file(ts_file, content)
                calls.extend(file_calls)
            except Exception as e:
                print(f"⚠️  {ts_file}: {e}")

        # 扫描 Python 文件
        for py_file in self.root.rglob('*.py'):
            if any(x in str(py_file) for x in ['node_modules', '.agent', 'venv', '__pycache__']):
                continue
            try:
                content = py_file.read_text(encoding='utf-8')
                file_calls = self._parse_python_file(py_file, content)
                calls.extend(file_calls)
            except Exception as e:
                print(f"⚠️  {py_file}: {e}")

        # 去重
        seen = set()
        unique = []
        for c in calls:
            key = (c.file, c.function)
            if key not in seen:
                seen.add(key)
                unique.append(c)

        self.api_calls = unique
        return unique

    def _parse_file(self, file_path: Path, content: str) -> List[APICall]:
        """解析TypeScript/JavaScript文件"""
        calls = []

        # 1. 查找导出的函数（一般函数和箭头函数）
        for match in re.finditer(r'(?:export\s+)?(?:async\s+)?(?:function|const)\s+(\w+)\s*(?:=\s*(?:async\s*)?\s*\(([^)]*)\)|\(([^)]*)\))', content):
            func_name = match.group(1)
            func_signature = match.group(2) or match.group(3) or ''
            func_start = match.end()

            arrow_pos = content.find('=>', func_start)
            if arrow_pos == -1 or arrow_pos > func_start + 500:
                brace_pos = content.find('{', func_start)
            else:
                brace_pos = content.find('{', arrow_pos)

            if brace_pos == -1:
                continue

            calls.extend(self._extract_and_analyze_body(content, brace_pos, match.start(), func_name, func_signature, file_path))

        # 2. 查找类方法或对象方法 (支持 async, static, public/private/protected 修饰符)
        for match in re.finditer(r'(?:(?:public|private|protected|static)\s+)*(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\s*\{', content):
            func_name = match.group(1)
            # 过滤掉一些常见的控制流关键字被误认为函数名
            if func_name in ['if', 'for', 'while', 'switch', 'catch', 'function', 'constructor']:
                continue
            
            func_signature = match.group(2) or ''
            brace_pos = match.end() - 1 
            calls.extend(self._extract_and_analyze_body(content, brace_pos, match.start(), func_name, func_signature, file_path))

        return calls

    def _extract_and_analyze_body(self, content: str, brace_pos: int, match_start: int, func_name: str, func_signature: str, file_path: Path) -> List[APICall]:
        """提取函数体并分析API调用"""
        depth = 0
        body_end = brace_pos
        for i in range(brace_pos, min(brace_pos + 10000, len(content))):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    body_end = i
                    break

        func_body = content[brace_pos:body_end]
        line_num = content[:match_start].count('\n') + 1

        image_params = self._extract_image_params(func_signature)
        call = self._analyze_function(func_name, func_body, str(file_path.relative_to(self.root)), line_num, image_params)
        
        return [call] if call else []

    def _extract_image_params(self, func_signature: str) -> List[str]:
        """从函数签名中提取图片类型参数"""
        image_params = []
        if not func_signature:
            return image_params

        # 方法1: 匹配参数名: 类型，其中类型包含 image/Image/reference/Reference 等关键词
        param_matches = re.findall(r'(\w+)\s*:\s*(?:[^,\n]*?)([Ii]mage|[Rr]eference|Picture|Photo|File|Base64|Data)', func_signature)
        for param_name, _ in param_matches:
            if param_name not in image_params:
                image_params.append(param_name)

        # 方法2: 直接检查参数名是否包含相关关键词
        all_params = re.findall(r'(\w+)\s*:', func_signature)
        for param_name in all_params:
            if any(kw in param_name.lower() for kw in ['image', 'img', 'photo', 'picture', 'file', 'base64', 'data', 'reference', 'ref']):
                if param_name not in image_params:
                    image_params.append(param_name)

        return image_params

    def _parse_python_file(self, file_path: Path, content: str) -> List[APICall]:
        """解析Python文件"""
        calls = []

        # 查找函数定义
        for match in re.finditer(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', content, re.M):
            func_name = match.group(1)
            func_start = match.end()

            # 找到函数体（缩进级别）
            lines_after = content[func_start:].split('\n')
            func_lines = []
            base_indent = len(lines_after[0]) - len(lines_after[0].lstrip()) if lines_after else 0

            for line in lines_after[1:]:
                if line.strip() and not line.startswith(base_indent * ' '):
                    break
                func_lines.append(line)

            func_body = '\n'.join(func_lines)
            line_num = content[:match.start()].count('\n') + 1

            call = self._analyze_function(func_name, func_body, str(file_path.relative_to(self.root)), line_num)
            if call:
                calls.append(call)

        return calls

    def _analyze_function(self, func_name: str, func_body: str, file_path: str, line_num: int, image_params: List[str] = None) -> Optional[APICall]:
        """分析函数体，检测API调用特征"""

        # 检测API调用标志
        has_api = any(keyword in func_body for keyword in [
            'fetch(', 'generateContent', 'streamGenerateContent',
            'callGeminiApi', 'gemini', 'generativelanguage'
        ])

        if not has_api:
            return None

        # 优先检测显式的 model 赋值 (如 model = 'gemini-3-pro-preview')
        explicit_model = self._extract_model_from_code(func_body)

        # 检测多模态特征
        # 注意：不使用 .lower() 以便匹配驼峰命名如 inlineData
        has_image = any(kw in func_body or kw in func_body.lower() for kw in [
            'image', 'inlineData', 'inline_data', 'base64.*image', 'photo', 'picture'
        ])
        has_audio = any(kw in func_body.lower() for kw in [
            'audio', 'tts', 'speech', 'voice', 'pcm', 'wav'
        ])
        has_video = any(kw in func_body.lower() for kw in [
            'video', 'mp4', 'webm'
        ])
        has_stream = 'stream' in func_body.lower() or 'streamgeneratecontent' in func_body.lower()
        has_tts = 'tts' in func_body.lower() or 'text_to_speech' in func_body.lower() or 'speechconfig' in func_body.lower()
        has_structured = 'json' in func_body.lower() and ('schema' in func_body.lower() or 'responsemime' in func_body.lower())

        # 提取参数
        params = self._extract_params(func_body)

        # 匹配模型 - 优先使用显式声明的模型
        detected_model, matched_config = self._match_model(
            func_name, has_image, has_audio, has_video, has_stream, has_tts, has_structured, explicit_model
        )

        return APICall(
            function=func_name,
            file=file_path,
            line=line_num,
            has_image=has_image,
            has_audio=has_audio,
            has_video=has_video,
            has_stream=has_stream,
            has_tts=has_tts,
            has_structured=has_structured,
            detected_model=detected_model,
            matched_config=matched_config,
            extracted_params=params,
            image_params=image_params or []
        )

    def _extract_params(self, func_body: str) -> Dict[str, Any]:
        """从函数体中提取参数"""
        params = {}

        # 提取 temperature
        temp_match = re.search(r'.temperature\s*[:=]\s*([\d.]+)', func_body, re.I)
        if temp_match:
            params['temperature'] = float(temp_match.group(1))

        # 提取 maxOutputTokens
        tokens_match = re.search(r'.maxOutputTokens\s*[:=]\s*(\d+)', func_body, re.I)
        if tokens_match:
            params['maxOutputTokens'] = int(tokens_match.group(1))

        # 提取 aspectRatio
        ar_match = re.search(r'.aspectRatio\s*[:=]\s*["\']([^"\']+)["\']', func_body, re.I)
        if ar_match:
            params.setdefault('imageConfig', {})['aspectRatio'] = ar_match.group(1)

        # 提取 imageSize
        size_match = re.search(r'.imageSize\s*[:=]\s*["\']([^"\']+)["\']', func_body, re.I)
        if size_match:
            params.setdefault('imageConfig', {})['imageSize'] = size_match.group(1)

        # 提取 systemInstruction
        if 'systemInstruction' in func_body or 'system_instruction' in func_body:
            params['systemInstruction'] = True

        # 提取 thinkingLevel
        thinking_match = re.search(r'.thinkingLevel\s*[:=]\s*["\']([^"\']+)["\']', func_body, re.I)
        if thinking_match:
            params.setdefault('thinkingConfig', {})['thinkingLevel'] = thinking_match.group(1)

        # 提取 voiceName
        voice_match = re.search(r'.voiceName\s*[:=]\s*["\']([^"\']+)["\']', func_body, re.I)
        if voice_match:
            params.setdefault('voiceConfig', {})['voiceName'] = voice_match.group(1)

        return params

    def _extract_model_from_code(self, func_body: str) -> Optional[str]:
        """从代码中提取显式声明的模型名称"""
        # 匹配 model = 'gemini-xxx' 或 model = "gemini-xxx"
        # 新增: 匹配 callGemini('gemini-xxx', ...) 模式
        patterns = [
            r"model\s*=\s*['\"](gemini-[\w\.-]+)['\"]",
            r"model:\s*['\"](gemini-[\w\.-]+)['\"]",
            r'["\']model["\']:\s*["\'](gemini-[\w\.-]+)["\']',
            r"callGemini\(\s*['\"](gemini-[\w\.-]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, func_body, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _match_model(
        self, func_name: str, has_image: bool, has_audio: bool, has_video: bool,
        has_stream: bool, has_tts: bool, has_structured: bool, explicit_model: Optional[str] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """根据特征匹配模型"""

        # 如果有显式声明的模型，直接使用
        if explicit_model:
            # 尝试匹配已知模型
            for model_id in self.model_configs:
                if model_id.lower() == explicit_model.lower():
                    return model_id, self.model_configs[model_id]
            # 如果是已知模型但不在配置中，返回基本配置
            return explicit_model, None

        # 优先级匹配（基于特征推断）
        if has_tts:
            return 'gemini-2.5-flash-preview-tts', self.model_configs.get('gemini-2.5-flash-preview-tts')

        if has_structured:
            return 'gemini-3-pro-preview', self.model_configs.get('gemini-3-pro-preview')

        if has_stream:
            return 'gemini-2.5-flash-stream', self.model_configs.get('gemini-2.5-flash-stream')

        if has_image:
            # 检查是否是高级图片生成
            func_lower = func_name.lower()
            if any(kw in func_lower for kw in ['grid', '4k', 'high', 'advanced', 'pro']):
                return 'gemini-3-pro-image-preview', self.model_configs.get('gemini-3-pro-image-preview')
            return 'gemini-2.5-flash-image', self.model_configs.get('gemini-2.5-flash-image')

        if has_audio or has_video:
            return 'gemini-2.5-flash', self.model_configs.get('gemini-2.5-flash')

        # 默认使用通用模型
        return 'gemini-2.0-flash-exp', self.model_configs.get('gemini-2.0-flash-exp')

    def get_rest_example(self, call: APICall) -> str:
        """生成REST调用示例"""
        if not call.matched_config:
            return "# 未匹配到模型配置"

        config = call.matched_config
        api_version = config.api_version
        base_url = "https://generativelanguage.googleapis.com"
        endpoint = config.endpoint
        model = call.detected_model

        # 构建请求体
        if call.has_tts:
            request_body = self._build_tts_request(call)
        elif call.has_image and ('image' in config.category or call.image_params):
            request_body = self._build_image_request(call)
        elif call.has_structured:
            request_body = self._build_structured_request(call)
        else:
            request_body = self._build_default_request(call)

        # 格式化为 JSON
        json_str = json.dumps(request_body, indent=2, ensure_ascii=False)
        json_safe = json_str.replace("'", "'\\''")

        return f'''curl -s -X POST \\
  "{base_url}/{api_version}/models/{model}:{endpoint}" \\
  -H "x-goog-api-key: $GEMINI_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{json_safe}'
'''

    def _build_default_request(self, call: APICall) -> Dict[str, Any]:
        """构建默认请求"""
        request = {
            "contents": [{
                "parts": [{"text": "{{prompt}}"}]
            }]
        }

        # 添加提取的参数
        gen_config = {}
        if 'temperature' in call.extracted_params:
            gen_config['temperature'] = call.extracted_params['temperature']
        if 'maxOutputTokens' in call.extracted_params:
            gen_config['maxOutputTokens'] = call.extracted_params['maxOutputTokens']

        if gen_config:
            request['generationConfig'] = gen_config

        return request

    def _build_image_request(self, call: APICall) -> Dict[str, Any]:
        """构建图片生成请求"""
        # 检查是否有图片参数（如 referenceImages）
        has_image_input = call.image_params and len(call.image_params) > 0

        if has_image_input:
            # 包含图片输入的请求 - 注意：请求使用 snake_case
            request = {
                "contents": [{
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": "BASE64_IMAGE_DATA"
                            }
                        },
                        {"text": "{{prompt}}"}
                    ]
                }]
            }
        else:
            # 纯文本生成的请求
            request = {
                "contents": [{
                    "parts": [{"text": "{{prompt}}"}]
                }]
            }

        # 添加图片配置
        if 'imageConfig' in call.extracted_params:
            if 'generationConfig' not in request:
                request['generationConfig'] = {}
            request['generationConfig']['imageConfig'] = call.extracted_params['imageConfig']

        return request

    def _build_tts_request(self, call: APICall) -> Dict[str, Any]:
        """构建TTS请求"""
        request = {
            "contents": [{
                "parts": [{"text": "{{text}}"}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": call.extracted_params.get('voiceConfig', {}).get('voiceName', 'Kore')
                        }
                    }
                }
            }
        }
        return request

    def _build_structured_request(self, call: APICall) -> Dict[str, Any]:
        """构建结构化输出请求"""
        request = {
            "contents": [{
                "parts": [{"text": "{{prompt}}"}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            }
        }

        # 如果有提取的 thinkingLevel，添加到配置中
        if 'thinkingConfig' in call.extracted_params:
            request['generationConfig']['thinkingConfig'] = call.extracted_params['thinkingConfig']

        return request

    def get_response_example(self, call: APICall) -> str:
        """生成响应示例"""
        if not call.matched_config:
            return "# 未匹配到模型配置"

        response = call.matched_config.response_example
        return json.dumps(response, indent=2, ensure_ascii=False)

    def print_report(self):
        """打印分析报告"""
        print("=" * 80)
        print("🔍 Gemini API 分析报告")
        print("=" * 80)
        print()

        if not self.api_calls:
            print("❌ 未找到API调用")
            return

        for i, call in enumerate(self.api_calls, 1):
            print(f"\n{'─' * 80}")
            print(f"## [{i}] {call.function}()")
            print(f"📁 文件: {call.file}:{call.line}")
            print(f"🤖 检测到模型: `{call.detected_model}`")

            if call.matched_config:
                print(f"📋 类别: {call.matched_config.category}")
                print(f"📝 描述: {call.matched_config.description}")

            # 特征标签
            tags = []
            if call.has_image: tags.append("🖼️ 图片")
            if call.has_audio: tags.append("🎵 音频")
            if call.has_video: tags.append("🎬 视频")
            if call.has_stream: tags.append("📡 流式")
            if call.has_tts: tags.append("🔊 语音")
            if call.has_structured: tags.append("📊 结构化")
            if tags:
                print(f"🏷️  特征: {' '.join(tags)}")

            # 提取的参数
            if call.extracted_params:
                print(f"⚙️  参数: {json.dumps(call.extracted_params, ensure_ascii=False)}")

            print("\n### REST 调用示例")
            print(self.get_rest_example(call))

            print("### 响应示例")
            print("```json")
            print(self.get_response_example(call))
            print("```")

    def generate_markdown(self) -> str:
        """生成Markdown报告"""
        lines = ["# Gemini API 分析报告\n"]
        lines.append(f"扫描时间: {Path(__file__).stat().st_mtime}\n")
        lines.append(f"发现 {len(self.api_calls)} 个API调用\n")

        # 模型统计
        model_count = {}
        for call in self.api_calls:
            model_count[call.detected_model] = model_count.get(call.detected_model, 0) + 1

        lines.append("## 模型使用统计\n")
        lines.append("| 模型 | 调用次数 |\n|---|---|\n")
        for model, count in sorted(model_count.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| `{model}` | {count} |\n")

        lines.append("\n---\n\n## API 调用详情\n")

        for i, call in enumerate(self.api_calls, 1):
            lines.append(f"### [{i}] `{call.function}()`\n")
            lines.append(f"- **文件**: `{call.file}:{call.line}`\n")
            lines.append(f"- **模型**: `{call.detected_model}`\n")

            if call.matched_config:
                lines.append(f"- **类别**: {call.matched_config.category}\n")
                lines.append(f"- **描述**: {call.matched_config.description}\n")

            # 特征
            features = []
            if call.has_image: features.append("图片")
            if call.has_audio: features.append("音频")
            if call.has_video: features.append("视频")
            if call.has_stream: features.append("流式")
            if call.has_tts: features.append("TTS")
            if call.has_structured: features.append("结构化输出")
            if features:
                lines.append(f"- **特征**: {', '.join(features)}\n")

            if call.extracted_params:
                lines.append(f"- **参数**: `{json.dumps(call.extracted_params, ensure_ascii=False)}`\n")

            lines.append("\n#### 推荐 REST 调用 (Standard)\n")
            lines.append("```bash\n")
            lines.append(self.get_rest_example(call))
            lines.append("```\n")

            lines.append("\n#### 响应示例\n")
            lines.append("```json\n")
            lines.append(self.get_response_example(call))
            lines.append("```\n")

            lines.append("\n---\n")

        return "".join(lines)

    def to_json(self) -> str:
        """导出JSON"""
        data = {
            "summary": {
                "total_calls": len(self.api_calls),
                "models_used": list(set(c.detected_model for c in self.api_calls))
            },
            "api_calls": []
        }

        for call in self.api_calls:
            call_data = {
                "function": call.function,
                "file": call.file,
                "line": call.line,
                "detected_model": call.detected_model,
                "features": {
                    "image": call.has_image,
                    "audio": call.has_audio,
                    "video": call.has_video,
                    "stream": call.has_stream,
                    "tts": call.has_tts,
                    "structured": call.has_structured
                },
                "extracted_params": call.extracted_params
            }

            if call.matched_config:
                call_data["model_info"] = {
                    "name": call.matched_config.name,
                    "category": call.matched_config.category,
                    "description": call.matched_config.description,
                    "api_version": call.matched_config.api_version,
                    "endpoint": call.matched_config.endpoint
                }

            data["api_calls"].append(call_data)

        return json.dumps(data, indent=2, ensure_ascii=False)


# ============================================
# Vibe Agent 风格调用
# ============================================

def analyze(project_dir: str = None, config_path: str = None) -> GeminiAnalyzer:
    """
    Vibe Agent 风格调用

    使用方式:
        analyzer = analyze()
        analyzer.print_report()
    """
    if project_dir is None:
        project_dir = Path(__file__).parents[4]

    if config_path is None:
        # 默认尝试从 resources 目录加载
        res_path = Path(__file__).parent.parent / "resources" / "gemini_models_config.json"
        if res_path.exists():
            config_path = res_path
        else:
            # 回退到同级目录
            config_path = Path(__file__).parent / "gemini_models_config.json"

    analyzer = GeminiAnalyzer(
        project_root=Path(project_dir),
        config_path=Path(config_path)
    )

    print("🔍 扫描源代码...")
    analyzer.scan()
    print(f"✅ 找到 {len(analyzer.api_calls)} 个API调用")

    return analyzer


def main():
    """命令行入口"""
    project_root = Path(__file__).parents[4]

    analyzer = analyze(str(project_root))

    # 生成报告
    output_dir = project_root
    md_report = analyzer.generate_markdown()
    json_data = analyzer.to_json()

    # 保存文件
    (output_dir / "gemini_api_analysis.md").write_text(md_report, encoding='utf-8')
    (output_dir / "gemini_api_analysis.json").write_text(json_data, encoding='utf-8')

    print(f"\n📄 报告已保存:")
    print(f"   - gemini_api_analysis.md")
    print(f"   - gemini_api_analysis.json")

    # 打印终端报告
    print()
    analyzer.print_report()


if __name__ == "__main__":
    main()
