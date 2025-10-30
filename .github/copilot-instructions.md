# Copilot Instructions - [YOUR_PROJECT_NAME]# Copilot Instructions - [YOUR_PROJECT_NAME]



## 📋 Project Overview##  Project Overview

[Describe your project in 2-3 sentences. What problem does it solve? Who uses it?][Describe your project in 2-3 sentences. What problem does it solve? Who uses it?]



**Example:****Example:**

> A web-based task management app that helps teams collaborate efficiently. > A web-based task management app that helps teams collaborate efficiently. 

> Built with React + Node.js, deployed on AWS. Focuses on simplicity and speed.> Built with React + Node.js, deployed on AWS. Focuses on simplicity and speed.



------



## 🛠️ Tech Stack##  Tech Stack



### **Languages & Frameworks**### **Languages & Frameworks**

- **Backend:** [e.g., Python 3.11, Node.js 18, Go 1.21]- **Backend:** [e.g., Python 3.11, Node.js 18, Go 1.21]

- **Frontend:** [e.g., React 18, Next.js 14, Vue 3]- **Frontend:** [e.g., React 18, Next.js 14, Vue 3]

- **Database:** [e.g., PostgreSQL 15, MongoDB 6, Redis]- **Database:** [e.g., PostgreSQL 15, MongoDB 6, Redis]

- **Infrastructure:** [e.g., AWS (Lambda, S3, RDS), Docker, Kubernetes]- **Infrastructure:** [e.g., AWS (Lambda, S3, RDS), Docker, Kubernetes]



### **Key Libraries**### **Key Libraries**

- [e.g., FastAPI for REST APIs]- [e.g., FastAPI for REST APIs]

- [e.g., Prisma for database ORM]- [e.g., Prisma for database ORM]

- [e.g., TailwindCSS for styling]- [e.g., TailwindCSS for styling]



------



## 🎨 Architecture Patterns##  Architecture Patterns



### **1. [Pattern Name - e.g., Repository Pattern]**### **1. [Pattern Name]**

[Brief description and when to use it][Brief description and when to use it]



**Example:****Example:**

> All database access goes through repository classes in `src/repositories/`.> **Repository Pattern**: All database access goes through repository classes.

> Never query the database directly from controllers or services.> Never query the database directly from controllers.



```typescript### **2. [Pattern Name]**

// ✅ CORRECT[Another important pattern in your codebase]

const users = await userRepository.findAll();

**Example:**

// ❌ WRONG> **Dependency Injection**: Use constructor injection for services.

const users = await prisma.user.findMany();> Makes testing easier and reduces coupling.

```

### **3. [Pattern Name]**

### **2. [Pattern Name - e.g., Error Handling]**[Third pattern]

[Another important pattern in your codebase]

---

**Example:**

> All API errors use custom error classes that extend `AppError`.##  Critical Files (Never Auto-Merge)

> Always include error codes for client handling.

List files/directories that require human review. The auto-reviewer will flag these.

### **3. [Pattern Name - e.g., Testing Strategy]**

[Third pattern]

**Example:**
> Unit tests for business logic, integration tests for APIs.
> Minimum 80% coverage required for new code.

---

## 🚫 Critical Files (Never Auto-Merge)

These files require human review before merging. Update this list for your project.

```yaml
# Authentication & Security
src/auth/:
  reason: "Security-critical authentication logic"

src/middleware/auth.ts:
  reason: "Token validation and session management"

# Payment Processing
src/services/payment/:
  reason: "Financial transactions - zero error tolerance"

# Database Migrations
migrations/:
  reason: "Database schema changes need DBA review"

# Infrastructure
.github/workflows/:
  reason: "CI/CD pipeline changes affect all deployments"

terraform/:
  reason: "Infrastructure as code - affects production systems"

docker-compose.yml:
  reason: "Container orchestration configuration"

# Configuration
.env.production:
  reason: "Production secrets and config"
```

---

## ✅ Testing Requirements

### **Unit Tests**
- Test all business logic functions
- Mock external dependencies (APIs, database)
- Run with: `npm test` or `pytest`

### **Integration Tests**
- Test API endpoints end-to-end
- Use test database (not production!)
- Run with: `npm run test:integration`

### **Coverage Goals**
- Minimum: 80% for new code
- Critical paths: 100% (auth, payments, etc.)

---

## 🔒 Safety Rules

**❌ NEVER do these things:**
- Commit API keys, secrets, or passwords
- Disable security middleware (auth, CORS, rate limiting)
- Use `eval()`, `exec()`, or similar dangerous functions
- Bypass input validation
- Log sensitive user data (passwords, credit cards, etc.)
- Deploy to production without tests passing

**✅ ALWAYS do these:**
- Validate all user input
- Use parameterized queries (prevent SQL injection)
- Sanitize HTML output (prevent XSS)
- Rate limit public APIs
- Log errors with context (but not secrets!)

---

## 📂 Project Structure

```
your-project/
├── src/
│   ├── controllers/     # HTTP request handlers
│   ├── services/        # Business logic
│   ├── repositories/    # Database access
│   ├── models/          # Data models / entities
│   ├── middleware/      # Express/Koa middleware
│   └── utils/           # Helper functions
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── migrations/          # Database migrations
└── docs/                # Documentation
```

---

## 🚀 Development Workflow

1. **Branch naming:** `feature/description`, `fix/description`, `chore/description`
2. **Commits:** Use conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
3. **Pull requests:** 
   - All changes go through PRs
   - PRs must pass CI checks
   - Safe changes auto-merge (docs, tests)
   - Code changes need approval
4. **Code review:** Look for logic errors, security issues, performance

---

## 🎯 Common Tasks

### **Adding a New API Endpoint**
1. Create controller in `src/controllers/`
2. Add route in `src/routes/`
3. Write service logic in `src/services/`
4. Add validation middleware
5. Write tests (unit + integration)
6. Update API documentation

### **Adding a New Database Model**
1. Create model in `src/models/`
2. Create migration in `migrations/`
3. Add repository in `src/repositories/`
4. Write tests
5. Update docs

### **Fixing a Bug**
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Add regression test if needed

---

## 💡 Performance Guidelines

- **Database queries:** Use indexes, avoid N+1 queries
- **API responses:** Paginate large datasets (max 100 items)
- **Caching:** Cache expensive computations (Redis)
- **Images:** Optimize and use CDN

---

## 📖 Documentation Standards

- All public functions have JSDoc/docstrings
- README updated when adding major features
- API changes documented in `docs/api.md`
- Architecture decisions recorded in `docs/decisions/`

---

## 🔗 Useful Links

- **Repository:** [link to your repo]
- **Documentation:** [link to docs]
- **Staging:** [staging environment URL]
- **Production:** [production URL]
- **Monitoring:** [monitoring dashboard]

---

## 📝 Notes for AI Agents

**This file helps the Autonomous Loop understand your project.**

- Be specific about patterns and conventions
- Update critical files list as project grows
- Add examples of good/bad code patterns
- Document any "gotchas" or non-obvious rules
- Keep this file up to date - it's AI's "memory" of your project!

---

**Last Updated:** [Date]
**Maintained By:** [Team/Person]
