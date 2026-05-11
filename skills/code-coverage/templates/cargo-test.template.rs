// Use this template for: Rust services (Actix-web, Axum, Tokio, Hyper).
// Requires: cargo test (stdlib). Optional: mockall, tokio::test for async.
// Coverage: cargo-tarpaulin (Linux) or cargo-llvm-cov (macOS).
// Replace all {{PLACEHOLDER}} tokens before use.

use std::sync::Arc;

use {{crate_path}}::{{module_path}}::{{{StructName}}, {{DepTrait}}};

// ─── Mock for {{DepTrait}} ────────────────────────────────────────────────────
// Use mockall crate: cargo add --dev mockall

#[cfg(test)]
use mockall::{automock, predicate::*};

#[cfg_attr(test, automock)]
trait {{DepTrait}} {
    fn {{dep_method}}(&self, input: {{InputType}}) -> Result<{{ReturnType}}, {{ErrorType}}>;
}

// ─── Unit Tests ───────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_sut(dep: impl {{DepTrait}} + 'static) -> {{StructName}} {
        {{StructName}}::new(Arc::new(dep))
    }

    // ─── Happy Path ───────────────────────────────────────────────────────────

    #[test]
    fn test_{{method_name}}_happy_path() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .with(eq({{HAPPY_PATH_INPUT}}))
            .times(1)
            .returning(|_| Ok({{DEP_RETURN_VALUE}}));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{method_name}}({{HAPPY_PATH_INPUT}});

        // Assert
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), {{EXPECTED_OUTPUT}});
    }

    // ─── Edge Case 1: empty / zero input ─────────────────────────────────────

    #[test]
    fn test_{{method_name}}_with_empty_input() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .returning(|_| Ok({{EDGE_CASE_1_DEP_RETURN}}));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{method_name}}({{EDGE_CASE_1_INPUT}});

        // Assert
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), {{EDGE_CASE_1_EXPECTED}});
    }

    // ─── Edge Case 2: boundary / maximum ─────────────────────────────────────

    #[test]
    fn test_{{method_name}}_at_boundary() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .returning(|_| Ok({{EDGE_CASE_2_DEP_RETURN}}));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{method_name}}({{EDGE_CASE_2_INPUT}});

        // Assert
        assert!(result.is_ok());
    }

    // ─── Negative Path: dependency error propagates ───────────────────────────

    #[test]
    fn test_{{method_name}}_propagates_dep_error() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .returning(|_| Err({{ErrorType}}::{{error_variant}}("{{ERROR_MESSAGE}}".into())));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{method_name}}({{HAPPY_PATH_INPUT}});

        // Assert
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("{{ERROR_MESSAGE}}"));
    }

    // ─── Async tests (use #[tokio::test] for async fn) ───────────────────────

    #[tokio::test]
    async fn test_{{async_method_name}}_happy_path_async() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .returning(|_| Ok({{DEP_RETURN_VALUE}}));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{async_method_name}}({{HAPPY_PATH_INPUT}}).await;

        // Assert
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), {{EXPECTED_OUTPUT}});
    }

    #[tokio::test]
    async fn test_{{async_method_name}}_error_propagates_async() {
        // Arrange
        let mut mock = Mock{{DepTrait}}::new();
        mock.expect_{{dep_method}}()
            .returning(|_| Err({{ErrorType}}::{{error_variant}}("async error".into())));

        let sut = make_sut(mock);

        // Act
        let result = sut.{{async_method_name}}({{HAPPY_PATH_INPUT}}).await;

        // Assert
        assert!(result.is_err());
    }
}
