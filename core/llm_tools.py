"""LLM 相关工具函数"""
import os
from openai import OpenAI
from typing import Optional
from core.config import Config
from core.api_key_manager import APIKeyManager 

def call_llm_api_for_tools(content: str, system_prompt: str = "", output_type: str = "text") -> str:
    """调用大模型 API 处理提示词
    
    Args:
        content: 用户提示词内容
        system_prompt: 系统提示词，默认为空
        output_type: 输出类型，可选 "text" 或 "json_object"，默认为 "text"
        
    Returns:
        LLM 返回的结果字符串
    """
    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=APIKeyManager.get_api_key(),
            base_url=Config.API_BASE_URL
        )
        
        messages_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        # 创建流式请求
        response = client.chat.completions.create(
            model=Config.model_name,
            messages=messages_list,
            stream=True,
            frequency_penalty=0,
            max_tokens=8192,
            presence_penalty=0,
            temperature=1.0,
            top_p=1,
            response_format={"type": output_type}
        )

        # 用于存储完整响应
        full_response = ""

        # 处理流式响应
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content

        return full_response.strip()
        
    except Exception as e:
        print(f"LLM API 调用失败: {str(e)}")
        return ""

def call_advanced_llm_api(content: str, system_prompt: str = "", output_type: str = "text") -> str:
    """调用大模型 API 处理提示词
    
    Args:
        content: 用户提示词内容
        system_prompt: 系统提示词，默认为空
        output_type: 输出类型，可选 "text" 或 "json_object"，默认为 "text"
        
    Returns:
        LLM 返回的结果字符串
    """
    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=APIKeyManager.get_api_key(),
            base_url=Config.API_BASE_URL
        )
        

        messages_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        # 创建流式请求
        response = client.chat.completions.create(
            model=Config.advanced_model_name,
            messages=messages_list,
            stream=True,
            frequency_penalty=0,
            max_tokens=8192,
            presence_penalty=0,
            temperature=1.0,
            top_p=1,
            response_format={"type": output_type}
        )

        # 用于存储完整响应
        full_response = ""

        # 处理流式响应
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content

        return full_response.strip()

    except Exception as e:
        print(f"LLM API 调用失败: {str(e)}")
        return ""

def summary_order_detail_by_llm(json_string: str) -> str:
    """调用大模型解读订单详情
    
    Args:
        json_string: 订单详情 JSON 字符串
        
    Returns:
        订单摘要字符串
    """
    prompt = """你需要根据订单查询接口响应的参数定义解读返回信息，以下为重要参数说明：
        @param order_status  enum<integer> <int32>  订单状态
            枚举值：
            11 : 待付款
            12 : 待发货
            21 : 已发货
            22 : 交易成功
            23 : 已退款
            24 : 交易关闭

        @param goods object 商品信息

        @param pay_time   integer <int32> 订单支付时间

        @param waybill_no string 快递单号
            示例值:
            SF23817389113

        @param express_name string 快递公司名称
            示例值:
            顺丰速运
        
        @param seller_remark  string  卖家备注
            示例值:
            疫情期间暂停发货
        请在思考后输出总结信息，使用自然的语言总结概括，只输出总结部分，不用展示细节
    """
    
    return call_llm_api_for_tools(
        content=json_string,
        system_prompt=prompt,
        output_type="text"
    )

