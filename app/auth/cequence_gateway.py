"""
Cequence AI Gateway integration for enhanced security
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

import httpx
from fastapi import Request, HTTPException, status
from pydantic import BaseModel

from ..utils.logger import logger


@dataclass
class SecurityEvent:
    """Security event from Cequence"""
    event_id: str
    timestamp: datetime
    event_type: str
    severity: str
    source_ip: str
    user_agent: str
    description: str
    risk_score: float
    recommended_action: str


class CequenceConfig(BaseModel):
    """Cequence configuration"""
    api_endpoint: str
    api_key: str
    tenant_id: str
    enabled: bool = True
    timeout: int = 5
    max_retries: int = 3
    rate_limit_enabled: bool = True
    threat_detection_enabled: bool = True
    analytics_enabled: bool = True


class CequenceGateway:
    """Cequence AI Gateway integration for API security"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client = None
        self.blocked_ips = set()
        self.suspicious_ips = set()
        self.rate_limits = {}
        
        if self.config.enabled:
            self._initialize_client()
        else:
            logger.warning("Cequence AI Gateway disabled")
    
    def _load_config(self) -> CequenceConfig:
        """Load Cequence configuration from environment"""
        return CequenceConfig(
            api_endpoint=os.getenv("CEQUENCE_API_ENDPOINT", ""),
            api_key=os.getenv("CEQUENCE_API_KEY", ""),
            tenant_id=os.getenv("CEQUENCE_TENANT_ID", ""),
            enabled=os.getenv("CEQUENCE_ENABLED", "false").lower() == "true",
            timeout=int(os.getenv("CEQUENCE_TIMEOUT", "5")),
            max_retries=int(os.getenv("CEQUENCE_MAX_RETRIES", "3")),
            rate_limit_enabled=os.getenv("CEQUENCE_RATE_LIMIT", "true").lower() == "true",
            threat_detection_enabled=os.getenv("CEQUENCE_THREAT_DETECTION", "true").lower() == "true",
            analytics_enabled=os.getenv("CEQUENCE_ANALYTICS", "true").lower() == "true"
        )
    
    def _initialize_client(self):
        """Initialize HTTP client for Cequence API"""
        if not self.config.api_endpoint or not self.config.api_key:
            logger.error("Cequence API endpoint or key not configured")
            self.config.enabled = False
            return
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-Tenant-ID": self.config.tenant_id
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.config.api_endpoint,
            headers=headers,
            timeout=self.config.timeout
        )
        
        logger.info("Cequence AI Gateway client initialized")
    
    async def analyze_request(self, request: Request) -> Dict[str, Any]:
        """Analyze incoming request for security threats"""
        if not self.config.enabled or not self.config.threat_detection_enabled:
            return {"allowed": True, "risk_score": 0.0}
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Check if IP is already blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - IP blocked"
            )
        
        # Rate limiting check
        if self.config.rate_limit_enabled:
            await self._check_rate_limit(client_ip, request.url.path)
        
        # Prepare request data for analysis
        request_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "source_ip": client_ip,
            "user_agent": user_agent,
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "content_length": request.headers.get("content-length", 0)
        }
        
        try:
            # Send to Cequence for analysis
            analysis_result = await self._send_for_analysis(request_data)
            
            # Process analysis result
            if analysis_result.get("blocked", False):
                self.blocked_ips.add(client_ip)
                logger.warning(f"Cequence blocked IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied - security threat detected"
                )
            
            risk_score = analysis_result.get("risk_score", 0.0)
            if risk_score > 0.7:
                self.suspicious_ips.add(client_ip)
                logger.warning(f"High risk IP detected: {client_ip} (score: {risk_score})")
            
            return {
                "allowed": True,
                "risk_score": risk_score,
                "recommendations": analysis_result.get("recommendations", []),
                "threat_indicators": analysis_result.get("threat_indicators", [])
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cequence analysis failed: {e}")
            # Fail open - allow request if analysis fails
            return {"allowed": True, "risk_score": 0.0, "error": str(e)}
    
    async def _send_for_analysis(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request data to Cequence for analysis"""
        if not self.client:
            return {"allowed": True, "risk_score": 0.0}
        
        try:
            response = await self.client.post(
                "/api/v1/analyze",
                json=request_data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Cequence API error: {response.status_code}")
                return {"allowed": True, "risk_score": 0.0}
                
        except httpx.TimeoutException:
            logger.warning("Cequence API timeout")
            return {"allowed": True, "risk_score": 0.0}
        except Exception as e:
            logger.error(f"Cequence API request failed: {e}")
            return {"allowed": True, "risk_score": 0.0}
    
    async def _check_rate_limit(self, client_ip: str, path: str):
        """Check rate limiting for client IP"""
        now = datetime.utcnow()
        minute_key = f"{client_ip}:{now.strftime('%Y-%m-%d-%H-%M')}"
        hour_key = f"{client_ip}:{now.strftime('%Y-%m-%d-%H')}"
        
        # Get rate limits from environment
        per_minute_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        per_hour_limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
        
        # Check minute limit
        if minute_key not in self.rate_limits:
            self.rate_limits[minute_key] = 0
        self.rate_limits[minute_key] += 1
        
        if self.rate_limits[minute_key] > per_minute_limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {self.rate_limits[minute_key]}/min")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded - too many requests per minute"
            )
        
        # Check hour limit
        if hour_key not in self.rate_limits:
            self.rate_limits[hour_key] = 0
        self.rate_limits[hour_key] += 1
        
        if self.rate_limits[hour_key] > per_hour_limit:
            logger.warning(f"Hourly rate limit exceeded for IP {client_ip}: {self.rate_limits[hour_key]}/hour")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded - too many requests per hour"
            )
        
        # Clean old rate limit entries
        await self._cleanup_rate_limits()
    
    async def _cleanup_rate_limits(self):
        """Clean up old rate limit entries"""
        now = datetime.utcnow()
        cutoff_minute = (now - timedelta(minutes=1)).strftime('%Y-%m-%d-%H-%M')
        cutoff_hour = (now - timedelta(hours=1)).strftime('%Y-%m-%d-%H')
        
        # Remove old entries
        keys_to_remove = []
        for key in self.rate_limits:
            if ':' in key:
                _, timestamp = key.rsplit(':', 1)
                if len(timestamp) == 13:  # minute format
                    if timestamp < cutoff_minute:
                        keys_to_remove.append(key)
                elif len(timestamp) == 10:  # hour format
                    if timestamp < cutoff_hour:
                        keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.rate_limits[key]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    async def log_security_event(self, event: SecurityEvent):
        """Log security event to Cequence"""
        if not self.config.enabled or not self.config.analytics_enabled:
            return
        
        event_data = {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "severity": event.severity,
            "source_ip": event.source_ip,
            "user_agent": event.user_agent,
            "description": event.description,
            "risk_score": event.risk_score,
            "recommended_action": event.recommended_action
        }
        
        try:
            if self.client:
                await self.client.post("/api/v1/events", json=event_data)
                logger.info(f"Logged security event: {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def log_analytics(self, analytics_data: Dict[str, Any]):
        """Log analytics data to Cequence"""
        if not self.config.enabled or not self.config.analytics_enabled:
            logger.debug("Cequence analytics disabled")
            return
        
        try:
            # Enhance analytics data with timestamp
            analytics_data["timestamp"] = datetime.utcnow().isoformat()
            analytics_data["tenant_id"] = self.config.tenant_id
            
            if self.client:
                response = await self.client.post(
                    "/api/v1/analytics",
                    json=analytics_data,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    logger.debug(f"Analytics logged successfully: {analytics_data.get('event_type', 'unknown')}")
                else:
                    logger.warning(f"Analytics logging failed with status: {response.status_code}")
            else:
                logger.debug("Cequence client not initialized - analytics not logged")
                
        except httpx.TimeoutException:
            logger.warning("Cequence analytics timeout")
        except Exception as e:
            logger.error(f"Failed to log analytics: {e}")

    async def get_threat_intelligence(self, ip: str) -> Dict[str, Any]:
        """Get threat intelligence for an IP address"""
        if not self.config.enabled or not self.client:
            return {}
        
        try:
            response = await self.client.get(f"/api/v1/threat-intel/{ip}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get threat intelligence: {e}")
        
        return {}
    
    async def block_ip(self, ip: str, reason: str, duration_hours: int = 24):
        """Temporarily block an IP address"""
        self.blocked_ips.add(ip)
        
        if self.config.enabled and self.client:
            try:
                block_data = {
                    "ip": ip,
                    "reason": reason,
                    "duration_hours": duration_hours,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.client.post("/api/v1/blocks", json=block_data)
                logger.info(f"Blocked IP {ip} for {duration_hours} hours: {reason}")
            except Exception as e:
                logger.error(f"Failed to register IP block: {e}")
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()


# Global gateway instance
gateway = CequenceGateway()
