import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class ExtractVariablesView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        prompt = request.data.get('prompt', '')
        # Matches brackets like [Target Audience], [Rule 1 - what to do], {{variable}}, or <variable>
        bracket_pattern = r'\[([^\]]+)\]'
        brace_pattern = r'\{\{([^\}]+)\}\}'
        angle_pattern = r'<([^>]+)>'
        
        variables = []
        for pattern in [bracket_pattern, brace_pattern, angle_pattern]:
            matches = re.finditer(pattern, prompt)
            for match in matches:
                var_name = match.group(1).split(' — ')[0].strip() # Clean up hints like "[Rule 1 — what to do]"
                if len(var_name) > 1 and var_name not in variables:
                    variables.append(var_name)
                    
        return Response({'variables': variables})
