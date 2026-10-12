"""
src/pulse/cells/response_encoding_cell.py

Response Encoding Cell.
Serializes the response Pulse into JSON or MessagePack based on content negotiation.
"""

from __future__ import annotations

import json
from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse


class ResponseEncodingCell(BaseCell):
    name = "ResponseEncodingCell"
    input_contract = Pulse
    output_contract = Pulse

    async def process(self, context: PulseContext) -> PulseContext:
        pulse_to_encode = context.response_pulse or context.current_pulse
        accept_header = context.incoming_pulse.integrity_metadata.get("accept", "")

        use_msgpack = "application/msgpack" in accept_header
        
        envelope_data = {
            "pulse_id": pulse_to_encode.pulse_id,
            "request_id": pulse_to_encode.request_id,
            "job_id": pulse_to_encode.job_id,
            "schema_version": pulse_to_encode.schema_version,
            "event_type": pulse_to_encode.event_type,
            "created_at_utc": pulse_to_encode.created_at_utc,
            "principal_id": pulse_to_encode.principal_id,
            "correlation_id": pulse_to_encode.correlation_id,
            "trace_id": pulse_to_encode.trace_id,
            "payload": pulse_to_encode.payload,
        }

        if use_msgpack:
            try:
                import msgpack
                encoded_bytes = msgpack.packb(envelope_data, use_bin_type=True)
                content_type = "application/msgpack"
            except ImportError:
                encoded_bytes = json.dumps(envelope_data).encode("utf-8")
                content_type = "application/json"
        else:
            encoded_bytes = json.dumps(envelope_data).encode("utf-8")
            content_type = "application/json"

        context.state["encoded_response"] = {
            "body": encoded_bytes,
            "content_type": content_type,
        }
        return context
