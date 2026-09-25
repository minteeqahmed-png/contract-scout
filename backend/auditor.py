import os
import json
import asyncio
from typing import Literal, Optional
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class NormalizedBBox(BaseModel):
    page_number: int
    left_pct: float
    top_pct: float
    width_pct: float
    height_pct: float

class ExtractedClause(BaseModel):
    text: str
    bbox: NormalizedBBox

class RuleVerdict(BaseModel):
    status: Literal["PASS", "FAIL", "RISK"]
    risk_severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    financial_exposure_estimate: str
    exposure_amount: Optional[float] = None
    is_unlimited_exposure: bool = False
    finding: str
    suggested_redline: Optional[str] = None

class RuleAuditResult(BaseModel):
    rule_id: str
    rule_name: str
    status: Literal["PASS", "FAIL", "RISK"]
    risk_severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    financial_exposure_estimate: str
    exposure_amount: Optional[float] = None
    is_unlimited_exposure: bool = False
    original_clause: Optional[ExtractedClause] = None
    finding: str
    suggested_redline: Optional[str] = None

class ContractAuditReport(BaseModel):
    report_id: str
    contract_title: str
    total_contract_value: Optional[str] = "Unknown"
    overall_bias_score: int
    total_financial_exposure: str
    has_unlimited_exposure: bool
    total_financial_exposure_amount: Optional[float] = None
    results: list[RuleAuditResult]
    page_count: int

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "dummy"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

async def extract_metadata(text: str) -> tuple[str, float]:
    """Extracts title and contract value."""
    prompt = f'Extract the Contract Title and Total Contract Value (as a numeric float) from the following text.\nRespond in JSON: {{"title": "", "value": 0.0}}\n\nText: {text[:4000]}'
    try:
        res = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        return data.get("title", "Unknown Contract"), float(data.get("value", 0.0))
    except Exception:
        return "Unknown Contract", 0.0

async def audit_rule(rule: dict, retrieved_chunks: list[dict], contract_value: float) -> RuleAuditResult:
    """Audits a single rule against retrieved text."""
    system_msg = "You are an expert legal contract auditor. Respond strictly in JSON matching the RuleVerdict schema."
    context = "\n\n".join(f"Clause (Page {c['bbox']['page_number']}): {c['text']}" for c in retrieved_chunks)
    prompt = f"""
    Rule: {rule['rule_name']}
    Requirement: {rule['standard_requirement']}
    Risk Trigger: {rule['risk_trigger']}
    Total Contract Value: ${contract_value:,.2f}
    
    Relevant Contract Text:
    {context}
    
    Evaluate the rule based on the relevant contract text. If the required clause is missing entirely, set status to FAIL.
    Return JSON only.
    """
    
    for attempt in range(2):
        try:
            res = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            if not res.choices:
                raise Exception(f"OpenRouter returned no choices! Raw response: {res}")
                
            data = json.loads(res.choices[0].message.content)
            
            # Apply financial logic manually just in case LLM misses it
            status = data.get("status", "FAIL")
            if status == "PASS":
                data["risk_severity"] = "NONE"
                data["financial_exposure_estimate"] = "$0 (Compliant)"
                data["exposure_amount"] = 0.0
                data["is_unlimited_exposure"] = False
            else:
                if rule["rule_name"] == "Liability Cap" and (data.get("is_unlimited_exposure") or "unlimited" in str(data.get("financial_exposure_estimate", "")).lower()):
                    data["is_unlimited_exposure"] = True
                    data["financial_exposure_estimate"] = "UNLIMITED EXPOSURE (Catastrophic)"
                    data["exposure_amount"] = None
                elif rule["rule_name"] == "Liquidated Damages" and data.get("exposure_amount"):
                    amt = data["exposure_amount"]
                    data["financial_exposure_estimate"] = f"Estimated ${amt:,.0f} penalty excess"
                    data["is_unlimited_exposure"] = False
            
            verdict = RuleVerdict.model_validate(data)
            top_chunk = retrieved_chunks[0] if retrieved_chunks else None
            return RuleAuditResult(
                rule_id=rule.get("rule_id", "Unknown"),
                rule_name=rule.get("rule_name", "Unknown"),
                status=verdict.status,
                risk_severity=verdict.risk_severity,
                financial_exposure_estimate=verdict.financial_exposure_estimate,
                exposure_amount=verdict.exposure_amount,
                is_unlimited_exposure=verdict.is_unlimited_exposure,
                original_clause=top_chunk if (verdict.status != "PASS" and top_chunk) else None,
                finding=verdict.finding,
                suggested_redline=verdict.suggested_redline
            )
        except ValidationError as e:
            prompt += f"\n\nJSON Validation Error on previous attempt. Fix it:\n{e.json()}"
            last_error = str(e)
        except Exception as e:
            import traceback
            print(f"Error calling LLM for rule '{rule.get('rule_name')}': {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            last_error = str(e)
            break
            
    # Hard failure fallback
    error_msg = f"Failed to process with LLM. Error: {last_error}" if 'last_error' in locals() else "Failed to parse LLM response after retries."
    
    if os.getenv("OPENAI_API_KEY", "dummy") == "dummy" or "AuthenticationError" in error_msg:
        error_msg = "🚨 API KEY ERROR: Please create a .env file with your OPENAI_API_KEY and restart the server."

    return RuleAuditResult(
        rule_id=rule.get("rule_id", "Unknown"),
        rule_name=rule.get("rule_name", "Unknown"),
        status="FAIL",
        risk_severity="HIGH",
        financial_exposure_estimate="Unknown Error during Audit",
        finding=error_msg,
        original_clause=None
    )

def calculate_bias_score(results: list[RuleAuditResult]) -> int:
    score = 0
    weights = {"CRITICAL": 35, "HIGH": 20, "MEDIUM": 10, "LOW": 5, "NONE": 0}
    for r in results:
        score += weights.get(r.risk_severity, 0)
    return min(100, score)

async def run_audit_pipeline(report_id: str, playbook: list[dict], extracted_clauses: list[dict], page_count: int, indexer) -> ContractAuditReport:
    full_text = " ".join(c["text"] for c in extracted_clauses)
    title, contract_value = await extract_metadata(full_text)
    
    tasks = []
    for rule in playbook:
        query = f"{rule['rule_name']} {rule['standard_requirement']}"
        top_chunks = indexer.hybrid_search(query, top_k=3)
        tasks.append(audit_rule(rule, top_chunks, contract_value))
        
    results = await asyncio.gather(*tasks)
    
    has_unlimited = any(r.is_unlimited_exposure for r in results)
    if has_unlimited:
        total_exp_amt = None
        total_exp_str = "UNLIMITED EXPOSURE (Catastrophic)"
    else:
        total_exp_amt = sum((r.exposure_amount or 0.0) for r in results)
        total_exp_str = f"${total_exp_amt:,.0f}"
        
    bias_score = calculate_bias_score(results)
    
    return ContractAuditReport(
        report_id=report_id,
        contract_title=title,
        total_contract_value=f"${contract_value:,.2f}",
        overall_bias_score=bias_score,
        total_financial_exposure=total_exp_str,
        has_unlimited_exposure=has_unlimited,
        total_financial_exposure_amount=total_exp_amt,
        results=results,
        page_count=page_count
    )
