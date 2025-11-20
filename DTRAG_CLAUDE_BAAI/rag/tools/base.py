from pydantic import BaseModel, Field
from abc import abstractmethod
from typing import get_type_hints, Dict, Any, List
import json


class BaseTool(BaseModel):
    toolCallID: str = Field(description="")

    @abstractmethod
    def exec(self):
        pass

    @classmethod
    def bingo_tool(cls, toolName):
        return cls.__name__ == toolName

    @classmethod
    def tool_load(cls, param, tool_call_id):
        print("json:", param)

        params = json.loads(param)
        params["toolCallID"] = tool_call_id
        return cls(**params)

    @classmethod
    def tool_define(cls):
        model = cls

        # 提取类描述
        class_description = model.__doc__.strip() if model.__doc__ else ""

        # 准备参数属性字典
        properties: Dict[str, Dict[str, Any]] = {}
        # 准备必需参数列表
        required: List[str] = []

        # 获取字段信息
        fields = model.model_fields

        for field_name, field in fields.items():
            if field_name == "toolCallID":
                continue

            # 字段类型映射
            type_mapping = {
                "int": "integer",
                "str": "string",
                # 添加更多Python类型到JSON Schema类型的映射
            }
            field_type = type_mapping.get(get_type_hints(
                model)[field_name].__name__, "string")

            # 字段描述
            field_description = field.description if field.description else ""

            # 检查字段是否为必需
            if field.is_required:
                required.append(field_name)

            # 组装参数属性
            properties[field_name] = {
                "type": field_type,
                "description": field_description,
            }

        # 组装函数定义
        function_spec = {
            "type": "function",
            "function": {
                "name": model.__name__,  # 假设函数名是类名的小写形式
                "description": class_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        }

        return function_spec
