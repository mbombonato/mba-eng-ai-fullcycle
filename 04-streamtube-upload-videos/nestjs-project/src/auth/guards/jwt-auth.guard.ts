import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { JwtService } from '@nestjs/jwt';
import { BEARER_PREFIX } from '../auth.constants';
import { JwtPayload } from '../auth.types';
import { IS_PUBLIC_KEY } from '../decorators/public.decorator';

type GuardedRequest = {
  headers: Record<string, string>;
  user?: JwtPayload;
};

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private readonly jwtService: JwtService,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    const request = context.switchToHttp().getRequest<GuardedRequest>();
    const token = this.extractBearerToken(request);

    if (isPublic) {
      // Optional authentication: public routes never reject, but a valid
      // token identifies the caller (e.g. the owner of a non-ready video).
      if (token) {
        request.user = await this.verifyOrUndefined(token);
      }
      return true;
    }

    if (!token) {
      throw new UnauthorizedException();
    }

    const payload = await this.verifyOrUndefined(token);
    if (!payload) {
      throw new UnauthorizedException();
    }
    request.user = payload;
    return true;
  }

  private extractBearerToken(request: GuardedRequest): string | undefined {
    const authHeader = request.headers?.authorization;
    if (!authHeader || !authHeader.startsWith(BEARER_PREFIX)) {
      return undefined;
    }
    return authHeader.slice(BEARER_PREFIX.length);
  }

  private async verifyOrUndefined(
    token: string,
  ): Promise<JwtPayload | undefined> {
    try {
      return await this.jwtService.verifyAsync<JwtPayload>(token);
    } catch {
      return undefined;
    }
  }
}
