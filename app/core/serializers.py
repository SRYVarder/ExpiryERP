from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenClaimsSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['role'] = user.role
        token['full_name'] = user.get_full_name() or user.username
        
        if hasattr(user, 'branch') and user.branch:
            token['branch_id'] = user.branch.id
            token['branch_name'] = user.branch.name
            
        return token